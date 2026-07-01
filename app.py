"""Streamlit chat UI for the BigQuery NL Chatbot."""

import streamlit as st

from bq_client import QueryTooExpensiveError, build_client, run_query
from config import load_config
from export import to_csv_bytes
from nl2sql import NL2SQLError, generate_sql
from schema_loader import load_schema
from sql_guard import SQLGuardError, validate_sql

st.set_page_config(page_title="BigQuery NL Chatbot", page_icon="📊")
st.title("📊 BigQuery NL Chatbot")
st.caption("Ask questions about your BigQuery data in plain English.")


@st.cache_resource
def get_config():
    return load_config()


@st.cache_resource
def get_bq_client(_config):
    return build_client(_config.gcp_project_id, _config.service_account_key_path)


@st.cache_resource(ttl=3600)
def get_schema(_config, _client):
    return load_schema(_client, _config.gcp_project_id, _config.dataset_whitelist)


try:
    config = get_config()
    client = get_bq_client(config)
    schema = get_schema(config, client)
except Exception as exc:
    st.error(f"Setup error: {exc}")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "query_history" not in st.session_state:
    st.session_state.query_history = []

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

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Translating to SQL..."):
                sql = generate_sql(
                    config.gemini_api_key,
                    config.gemini_model,
                    schema,
                    st.session_state.query_history,
                    question,
                )
                safe_sql = validate_sql(
                    sql, config.gcp_project_id, config.dataset_whitelist, config.max_rows
                )

            with st.spinner("Running query against BigQuery..."):
                df, bytes_processed = run_query(client, safe_sql, config.max_bytes_billed)

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
