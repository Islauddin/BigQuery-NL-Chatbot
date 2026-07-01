"""Streamlit chat UI for the BigQuery NL Chatbot.

First phase: a setup form collects the client's own service account key,
GCP project ID, dataset ID(s), and Gemini API key, and validates the
connection. Second phase: the chat interface, unlocked once setup succeeds.
"""

import json

import streamlit as st

from bq_client import QueryTooExpensiveError, build_client, run_query
from config import DEFAULT_GEMINI_MODEL, DEFAULT_MAX_BYTES_BILLED, DEFAULT_MAX_ROWS, build_config
from export import to_csv_bytes
from nl2sql import NL2SQLError, generate_sql
from schema_loader import load_schema
from sql_guard import SQLGuardError, validate_sql

st.set_page_config(page_title="BigQuery NL Chatbot", page_icon="📊")


def _render_setup_form():
    st.title("📊 BigQuery NL Chatbot")
    st.caption(
        "Connect your own BigQuery project to start asking questions in plain English. "
        "Nothing you enter here is written to disk — it's held in memory for this session only."
    )

    with st.form("setup_form"):
        key_file = st.file_uploader(
            "Service account JSON key (read-only BigQuery access)", type="json"
        )
        project_id = st.text_input(
            "GCP Project ID", placeholder="my-gcp-project (defaults to the key's project if blank)"
        )
        dataset_ids = st.text_input(
            "BigQuery Dataset ID(s)", placeholder="sales, marketing"
        )
        gemini_api_key = st.text_input("Gemini API Key", type="password")

        with st.expander("Advanced settings"):
            gemini_model = st.text_input("Gemini model", value=DEFAULT_GEMINI_MODEL)
            max_bytes_billed_mb = st.number_input(
                "Max scan allowed per query (MB)",
                min_value=1,
                value=DEFAULT_MAX_BYTES_BILLED // 1_000_000,
            )
            max_rows = st.number_input(
                "Max rows returned per query", min_value=1, value=DEFAULT_MAX_ROWS
            )

        submitted = st.form_submit_button("Connect")

    if not submitted:
        return

    if key_file is None:
        st.error("Please upload a service account JSON key.")
        return

    try:
        service_account_info = json.loads(key_file.getvalue())
    except json.JSONDecodeError:
        st.error(
            "That file isn't valid JSON. Upload the service account key exactly as "
            "downloaded from GCP."
        )
        return

    try:
        config = build_config(
            project_id=project_id or service_account_info.get("project_id", ""),
            dataset_whitelist_raw=dataset_ids,
            gemini_api_key=gemini_api_key,
            gemini_model=gemini_model,
            max_bytes_billed=int(max_bytes_billed_mb) * 1_000_000,
            max_rows=int(max_rows),
        )
    except ValueError as exc:
        st.error(str(exc))
        return

    with st.spinner("Connecting to BigQuery and reading schema..."):
        try:
            client = build_client(config.project_id, service_account_info)
            schema = load_schema(client, config.project_id, config.dataset_whitelist)
        except Exception as exc:
            st.error(f"Couldn't connect: {exc}")
            return

    st.session_state.config = config
    st.session_state.bq_client = client
    st.session_state.schema = schema
    st.session_state.messages = []
    st.session_state.query_history = []
    st.rerun()


def _render_chat():
    config = st.session_state.config

    with st.sidebar:
        st.subheader("Connection")
        st.text(f"Project: {config.project_id}")
        st.text("Datasets: " + ", ".join(config.dataset_whitelist))
        if st.button("Reconfigure"):
            for key in ("config", "bq_client", "schema", "messages", "query_history"):
                st.session_state.pop(key, None)
            st.rerun()

    st.title("📊 BigQuery NL Chatbot")
    st.caption("Ask questions about your BigQuery data in plain English.")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sql"):
                with st.expander("Generated SQL"):
                    st.code(message["sql"], language="sql")
            if message.get("df") is not None:
                st.dataframe(message["df"])
                st.download_button(
                    "Download CSV",
                    data=to_csv_bytes(message["df"]),
                    file_name="query_results.csv",
                    mime="text/csv",
                    key=message["download_key"],
                )

    question = st.chat_input("Ask a question about your data...")
    if not question:
        return

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Translating to SQL..."):
                sql = generate_sql(
                    config.gemini_api_key,
                    config.gemini_model,
                    st.session_state.schema,
                    st.session_state.query_history,
                    question,
                )
                safe_sql = validate_sql(
                    sql, config.project_id, config.dataset_whitelist, config.max_rows
                )

            with st.spinner("Running query against BigQuery..."):
                df, bytes_processed = run_query(
                    st.session_state.bq_client, safe_sql, config.max_bytes_billed
                )

            st.session_state.query_history.append({"question": question, "sql": safe_sql})

            content = f"Found {len(df)} row(s), scanned {bytes_processed / 1e6:.1f} MB."
            st.markdown(content)
            with st.expander("Generated SQL"):
                st.code(safe_sql, language="sql")
            st.dataframe(df)

            download_key = f"download_{len(st.session_state.messages)}"
            st.download_button(
                "Download CSV",
                data=to_csv_bytes(df),
                file_name="query_results.csv",
                mime="text/csv",
                key=download_key,
            )

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": content,
                    "sql": safe_sql,
                    "df": df,
                    "download_key": download_key,
                }
            )
        except (NL2SQLError, SQLGuardError, QueryTooExpensiveError) as exc:
            st.error(str(exc))
            st.session_state.messages.append({"role": "assistant", "content": f"⚠️ {exc}"})
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")
            st.session_state.messages.append(
                {"role": "assistant", "content": f"⚠️ Unexpected error: {exc}"}
            )


if "config" not in st.session_state:
    _render_setup_form()
else:
    _render_chat()
