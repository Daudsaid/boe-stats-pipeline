# etl/extract.py

import requests
import pandas as pd
import os
from io import StringIO
from config.settings import (
    BOE_API_BASE_URL,
    SERIES_CODES,
    CSV_FORMAT,
    USING_CODES,
    VPD,
    DEFAULT_START_DATE,
    DEFAULT_END_DATE,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    RAW_DATA_PATH,
)

def fetch_series(series_name: str, start_date: str = DEFAULT_START_DATE, end_date: str = DEFAULT_END_DATE) -> pd.DataFrame:
    """Fetch a single BoE series and return as a DataFrame."""
    series_code = SERIES_CODES.get(series_name)
    if not series_code:
        raise ValueError(f"Unknown series: {series_name}. Available: {list(SERIES_CODES.keys())}")

    params = {
        "csv.x": "yes",
        "Datefrom": start_date,
        "Dateto": end_date,
        "SeriesCodes": series_code,
        "CSVF": CSV_FORMAT,
        "UsingCodes": USING_CODES,
        "VPD": VPD,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(BOE_API_BASE_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            df = pd.read_csv(StringIO(response.text))
            df.columns = ["date", series_name]
            df["date"] = pd.to_datetime(df["date"], format="%d %b %Y")
            df["series_code"] = series_code
            df["extracted_at"] = pd.Timestamp.now()
            print(f"[extract] {series_name} — {len(df)} rows fetched")
            return df
        except Exception as e:
            print(f"[extract] Attempt {attempt} failed for {series_name}: {e}")
            if attempt == MAX_RETRIES:
                raise


def fetch_all_series() -> dict:
    """Fetch all series defined in SERIES_CODES."""
    results = {}
    for series_name in SERIES_CODES:
        results[series_name] = fetch_series(series_name)
    return results


def save_raw(df: pd.DataFrame, series_name: str) -> str:
    """Save raw DataFrame to CSV in data/raw/."""
    os.makedirs(RAW_DATA_PATH, exist_ok=True)
    filepath = os.path.join(RAW_DATA_PATH, f"{series_name}.csv")
    df.to_csv(filepath, index=False)
    print(f"[extract] Saved → {filepath}")
    return filepath


if __name__ == "__main__":
    all_data = fetch_all_series()
    for name, df in all_data.items():
        save_raw(df, name)