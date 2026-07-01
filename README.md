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

2. Create a GCP service account with **read-only** BigQuery access
   (`roles/bigquery.dataViewer` + `roles/bigquery.jobUser`), download its
   JSON key.

3. Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/).

4. Copy `.env.example` to `.env` and fill in your values:

   ```bash
   cp .env.example .env
   ```

5. Run the app:

   ```bash
   streamlit run app.py
   ```

## Configuration

All configuration lives in `.env` (see `.env.example`):

| Variable | Description |
| --- | --- |
| `GEMINI_API_KEY` | API key from Google AI Studio |
| `GEMINI_MODEL` | Gemini model name (default `gemini-2.5-flash`) |
| `GCP_PROJECT_ID` | GCP project the service account/queries run against |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to the service account JSON key |
| `DATASET_WHITELIST` | Comma-separated dataset IDs the app is allowed to see/query |
| `MAX_BYTES_BILLED` | Refuse queries estimated to scan more than this many bytes |
| `MAX_ROWS` | Row limit auto-appended to generated queries without one |

## Safety notes

- The service account used should be **read-only** — the app's SQL
  guardrail is a second layer of defense, not the only one.
- `DATASET_WHITELIST` restricts which datasets the LLM is even shown, and
  which tables generated SQL is allowed to reference.
- `MAX_BYTES_BILLED` prevents runaway queries from scanning your entire
  warehouse and racking up cost.

## Project structure

```
app.py            Streamlit chat UI
config.py         Environment/config loader
schema_loader.py  Pulls live schema from BigQuery INFORMATION_SCHEMA
nl2sql.py         Gemini-based NL → SQL translation
sql_guard.py       Validates/sanitizes generated SQL
bq_client.py      BigQuery execution with dry-run cost check
export.py         DataFrame → CSV bytes for download
```

## Roadmap ideas

- Swap `st.download_button` for a GCS signed URL if deploying somewhere
  that needs a persistent shareable link
- Add chart auto-generation for numeric results
- Support multi-turn query refinement with explicit "edit last query" intent
- Add per-user query audit logging
