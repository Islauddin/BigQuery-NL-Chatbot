# 📊 BigQuery NL Chatbot

Ask questions about your BigQuery data in plain English. The app translates
your question into SQL using Gemini, runs it safely against BigQuery, shows
the results, and lets you download them as a CSV.

## How it works

```
Your question
    → Gemini translates it to SQL (grounded on real BigQuery schema)
    → SQL guardrail checks it (SELECT-only, whitelisted tables, row limit)
    → BigQuery dry-run estimates cost, then executes
    → Results shown in-app + downloadable as CSV
```

## Features

- Chat-style UI built with Streamlit
- **Fully self-serve setup** — no `.env` file to configure. On first load, the
  app asks the client for their own service account key, GCP project ID,
  dataset ID(s), and Gemini API key, then validates the connection before
  unlocking the chat
- Schema-aware: reads real table/column names from `INFORMATION_SCHEMA` so
  the LLM doesn't guess
- SQL guardrails: blocks any non-SELECT statement, restricts queries to a
  dataset whitelist, auto-limits row counts
- Cost control: dry-runs every query first and refuses to run anything over
  a configurable byte-scan threshold
- One-click CSV download of any result set
- Follow-up questions work (e.g. "now filter by region")

## Setup

1. Clone the repo and install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Run the app:

   ```bash
   streamlit run app.py
   ```

3. On the setup screen, provide:

   - **Service account JSON key** — create a GCP service account with
     **read-only** BigQuery access (`roles/bigquery.dataViewer` +
     `roles/bigquery.jobUser`), download its JSON key, and upload it here.
     It's parsed in memory for this session only and never written to disk.
   - **GCP Project ID** — defaults to the project embedded in the key if
     left blank.
   - **BigQuery Dataset ID(s)** — comma-separated (e.g. `sales, marketing`).
     Only these datasets are shown to the LLM and are queryable.
   - **Gemini API Key** — from [Google AI Studio](https://aistudio.google.com/).
   - *(Optional, under "Advanced settings")* Gemini model, max scan size per
     query (MB), max rows returned.

   Clicking **Connect** validates the credentials by reading the schema; on
   success the chat interface unlocks. Use the **Reconfigure** button in the
   sidebar at any time to disconnect and set up a different project.

## Safety notes

- The service account used should be **read-only** — the app's SQL
  guardrail is a second layer of defense, not the only one.
- The dataset whitelist entered at setup restricts which datasets the LLM is
  even shown, and which tables generated SQL is allowed to reference.
- The max-scan setting prevents runaway queries from scanning your entire
  warehouse and racking up cost.
- Uploaded keys and API keys live only in that browser session's server-side
  memory (`st.session_state`) — they're discarded when the session ends or
  "Reconfigure" is clicked.

## Project structure

```
app.py            Streamlit chat UI: setup form (phase 1) + chat (phase 2)
config.py         Config model + validation for setup-form input
schema_loader.py  Pulls live schema from BigQuery INFORMATION_SCHEMA
nl2sql.py         Gemini-based NL → SQL translation (google-genai SDK)
sql_guard.py      Validates/sanitizes generated SQL
bq_client.py      BigQuery execution with dry-run cost check
export.py         DataFrame → CSV bytes for download
requirements.txt  Python dependencies
.gitignore        Keeps stray key files, .env, __pycache__ out of git
```

## Roadmap ideas

- Swap `st.download_button` for a GCS signed URL if deploying somewhere
  that needs a persistent shareable link
- Add chart auto-generation for numeric results
- Support multi-turn query refinement with explicit "edit last query" intent
- Add per-user query audit logging
