"""Reads live table/column metadata from BigQuery INFORMATION_SCHEMA.

Grounding the LLM on the real schema (instead of letting it guess table and
column names) is what keeps generated SQL from hallucinating references that
don't exist.
"""

from google.cloud import bigquery


def load_schema(client: bigquery.Client, project_id: str, dataset_whitelist) -> str:
    """Return a text description of every table/column in the whitelisted datasets."""
    sections = []

    for dataset in dataset_whitelist:
        query = f"""
            SELECT table_name, column_name, data_type
            FROM `{project_id}.{dataset}`.INFORMATION_SCHEMA.COLUMNS
            ORDER BY table_name, ordinal_position
        """
        rows = client.query(query).result()

        tables = {}
        for row in rows:
            tables.setdefault(row.table_name, []).append(f"{row.column_name} ({row.data_type})")

        for table_name, columns in tables.items():
            fq_name = f"{project_id}.{dataset}.{table_name}"
            sections.append(f"Table `{fq_name}`:\n  " + "\n  ".join(columns))

    if not sections:
        raise RuntimeError(
            "No tables found in the whitelisted datasets. Check DATASET_WHITELIST and "
            "the service account's permissions."
        )

    return "\n\n".join(sections)
