"""Validates LLM-generated SQL before it's allowed to run against BigQuery.

This is a second layer of defense on top of the read-only service account:
SELECT-only, whitelisted tables only, single statement, row-limited.
"""

import re

import sqlparse

_FORBIDDEN_KEYWORDS = (
    "insert", "update", "delete", "merge", "drop", "create", "alter",
    "truncate", "grant", "revoke", "call", "execute", "load",
)

_TABLE_REF_RE = re.compile(r"`?([\w-]+)`?\.`?([\w-]+)`?\.`?([\w-]+)`?")


class SQLGuardError(ValueError):
    pass


def validate_sql(sql: str, project_id: str, dataset_whitelist, max_rows: int) -> str:
    """Raises SQLGuardError if sql is unsafe; otherwise returns sql with a LIMIT applied."""
    if not sql or not sql.strip():
        raise SQLGuardError("Generated SQL is empty.")

    cleaned = sql.strip().rstrip(";")
    if ";" in cleaned:
        raise SQLGuardError("Only a single SQL statement is allowed.")

    parsed = [s for s in sqlparse.parse(cleaned) if s.token_first(skip_cm=True) is not None]
    if len(parsed) != 1:
        raise SQLGuardError("Only a single SQL statement is allowed.")

    first_token = parsed[0].token_first(skip_cm=True)
    if first_token.value.upper() not in ("SELECT", "WITH"):
        raise SQLGuardError("Only SELECT statements are allowed.")

    lowered = cleaned.lower()
    for keyword in _FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", lowered):
            raise SQLGuardError(f"Query contains a forbidden keyword: {keyword.upper()}")

    tables = _TABLE_REF_RE.findall(cleaned)
    if not tables:
        raise SQLGuardError(
            "Query must reference fully-qualified tables (project.dataset.table)."
        )

    for ref_project, dataset, _table in tables:
        if ref_project != project_id:
            raise SQLGuardError(f"Query references an unexpected project: {ref_project}")
        if dataset not in dataset_whitelist:
            raise SQLGuardError(f"Query references a dataset outside the whitelist: {dataset}")

    return _ensure_row_limit(cleaned, max_rows)


def _ensure_row_limit(sql: str, max_rows: int) -> str:
    if re.search(r"\blimit\s+\d+", sql, re.IGNORECASE):
        return sql
    return f"{sql}\nLIMIT {max_rows}"
