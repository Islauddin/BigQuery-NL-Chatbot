"""Config model + validation for values collected from the client-side setup form."""

from dataclasses import dataclass

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_MAX_BYTES_BILLED = 100_000_000  # 100 MB
DEFAULT_MAX_ROWS = 1000


@dataclass(frozen=True)
class Config:
    project_id: str
    dataset_whitelist: tuple
    gemini_api_key: str
    gemini_model: str
    max_bytes_billed: int
    max_rows: int


def build_config(
    *,
    project_id: str,
    dataset_whitelist_raw: str,
    gemini_api_key: str,
    gemini_model: str = "",
    max_bytes_billed: int = DEFAULT_MAX_BYTES_BILLED,
    max_rows: int = DEFAULT_MAX_ROWS,
) -> Config:
    """Validates raw setup-form input and returns an immutable Config, or raises ValueError."""
    project_id = (project_id or "").strip()
    if not project_id:
        raise ValueError("GCP Project ID is required.")

    dataset_whitelist = tuple(
        dict.fromkeys(d.strip() for d in (dataset_whitelist_raw or "").split(",") if d.strip())
    )
    if not dataset_whitelist:
        raise ValueError("At least one BigQuery dataset ID is required.")

    gemini_api_key = (gemini_api_key or "").strip()
    if not gemini_api_key:
        raise ValueError("Gemini API key is required.")

    return Config(
        project_id=project_id,
        dataset_whitelist=dataset_whitelist,
        gemini_api_key=gemini_api_key,
        gemini_model=(gemini_model or DEFAULT_GEMINI_MODEL).strip(),
        max_bytes_billed=int(max_bytes_billed),
        max_rows=int(max_rows),
    )
