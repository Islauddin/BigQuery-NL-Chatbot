"""Translates a natural-language question into BigQuery Standard SQL using Gemini."""

import re

from google import genai
from google.genai import types

_SYSTEM_INSTRUCTION = """You are a BigQuery SQL expert. Convert the user's question into a single
BigQuery Standard SQL SELECT statement.

Rules:
- Only use the tables and columns listed in the schema below. Never invent table or column names.
- Only ever write a single SELECT statement. Never write INSERT, UPDATE, DELETE, MERGE, DROP,
  CREATE, ALTER, TRUNCATE, or any other DDL/DML.
- Never use scripting, multiple statements, or semicolons.
- Always fully-qualify table names as `project.dataset.table`.
- If the question is a follow-up (e.g. "now filter by region"), use the conversation history
  to understand what it refines.
- Return ONLY the SQL. No explanation, no markdown code fences.

Schema:
{schema}
"""


class NL2SQLError(RuntimeError):
    pass


def _extract_sql(text: str) -> str:
    text = text.strip()
    fence_match = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1).strip()
    return text.rstrip(";").strip()


def generate_sql(api_key: str, model_name: str, schema: str, history: list, question: str) -> str:
    """history is a list of {"question": str, "sql": str} from prior turns in this session."""
    client = genai.Client(api_key=api_key)

    chat_history = []
    for turn in history:
        chat_history.append(
            types.Content(role="user", parts=[types.Part(text=turn["question"])])
        )
        chat_history.append(
            types.Content(role="model", parts=[types.Part(text=turn["sql"])])
        )

    chat = client.chats.create(
        model=model_name,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_INSTRUCTION.format(schema=schema),
        ),
        history=chat_history,
    )

    try:
        response = chat.send_message(question)
    except Exception as exc:
        raise NL2SQLError(f"Gemini request failed: {exc}") from exc

    if not response.text:
        raise NL2SQLError("Gemini returned no SQL. Try rephrasing your question.")

    sql = _extract_sql(response.text)
    if not sql:
        raise NL2SQLError("Gemini returned an empty response.")
    return sql
