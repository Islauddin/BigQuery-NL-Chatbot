"""Loads and validates configuration from environment variables / .env."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    gemini_api_key: str
    gemini_model: str
    gcp_project_id: str
    service_account_key_path: str
    dataset_whitelist: tuple
    max_bytes_billed: int
    max_rows: int


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_config() -> Config:
    whitelist = tuple(
        d.strip() for d in os.environ.get("DATASET_WHITELIST", "").split(",") if d.strip()
    )
    if not whitelist:
        raise RuntimeError(
            "DATASET_WHITELIST must list at least one dataset (comma-separated)."
        )

    return Config(
        gemini_api_key=_require("GEMINI_API_KEY"),
        gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
        gcp_project_id=_require("GCP_PROJECT_ID"),
        service_account_key_path=_require("GOOGLE_APPLICATION_CREDENTIALS"),
        dataset_whitelist=whitelist,
        max_bytes_billed=int(os.environ.get("MAX_BYTES_BILLED", 100_000_000)),
        max_rows=int(os.environ.get("MAX_ROWS", 1000)),
    )
