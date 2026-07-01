"""DataFrame -> CSV bytes, for Streamlit's download_button."""

import pandas as pd


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")
