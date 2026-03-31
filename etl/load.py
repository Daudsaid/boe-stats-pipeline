# etl/load.py

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", 5432),
    "dbname": os.getenv("DB_NAME", "boe_pipeline"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

RAW_DATA_PATH = "data/raw"


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def create_table(conn, series_name: str):
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS raw_{series_name} (
                id          SERIAL PRIMARY KEY,
                date        DATE NOT NULL,
                value       NUMERIC,
                series_code VARCHAR(20),
                extracted_at TIMESTAMP,
                UNIQUE(date)
            );
        """)
    conn.commit()
    print(f"[load] Table raw_{series_name} ready")


def load_series(conn, series_name: str):
    filepath = os.path.join(RAW_DATA_PATH, f"{series_name}.csv")
    df = pd.read_csv(filepath, parse_dates=["date"])

    rows = [
        (
            row["date"].date(),
            row[series_name] if pd.notna(row[series_name]) else None,
            row["series_code"],
            row["extracted_at"],
        )
        for _, row in df.iterrows()
    ]

    with conn.cursor() as cur:
        execute_values(cur, f"""
            INSERT INTO raw_{series_name} (date, value, series_code, extracted_at)
            VALUES %s
            ON CONFLICT (date) DO UPDATE
                SET value = EXCLUDED.value,
                    extracted_at = EXCLUDED.extracted_at;
        """, rows)

    conn.commit()
    print(f"[load] {series_name} — {len(rows)} rows loaded into raw_{series_name}")


def load_all(series_list: list):
    conn = get_connection()
    try:
        for series_name in series_list:
            create_table(conn, series_name)
            load_series(conn, series_name)
    finally:
        conn.close()


if __name__ == "__main__":
    from config.settings import SERIES_CODES
    load_all(list(SERIES_CODES.keys()))