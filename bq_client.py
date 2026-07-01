"""BigQuery execution with a dry-run cost check before every real query."""

from google.cloud import bigquery
from google.oauth2 import service_account


class QueryTooExpensiveError(RuntimeError):
    def __init__(self, bytes_processed: int, max_bytes_billed: int):
        self.bytes_processed = bytes_processed
        self.max_bytes_billed = max_bytes_billed
        super().__init__(
            f"Query would scan {bytes_processed / 1e9:.2f} GB, which exceeds the "
            f"configured limit of {max_bytes_billed / 1e9:.2f} GB."
        )


def build_client(project_id: str, service_account_key_path: str) -> bigquery.Client:
    credentials = service_account.Credentials.from_service_account_file(
        service_account_key_path
    )
    return bigquery.Client(project=project_id, credentials=credentials)


def estimate_bytes_processed(client: bigquery.Client, sql: str) -> int:
    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    job = client.query(sql, job_config=job_config)
    return job.total_bytes_processed


def run_query(client: bigquery.Client, sql: str, max_bytes_billed: int):
    """Dry-runs sql for a cost estimate, then executes it if under budget.

    Returns (dataframe, bytes_processed).
    """
    bytes_processed = estimate_bytes_processed(client, sql)
    if bytes_processed > max_bytes_billed:
        raise QueryTooExpensiveError(bytes_processed, max_bytes_billed)

    job_config = bigquery.QueryJobConfig(maximum_bytes_billed=max_bytes_billed)
    job = client.query(sql, job_config=job_config)
    return job.result().to_dataframe(), bytes_processed
