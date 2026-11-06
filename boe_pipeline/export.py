"""Export dbt marts to Parquet for the Streamlit app.

The app reads these small files (well under 1 MB) straight from the repo, so
Streamlit Cloud needs no database connection or secrets. The scheduled refresh
workflow re-runs this and commits the result, which triggers a redeploy.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = PROJECT_ROOT / "app" / "data"

MARTS = (
    "fct_bank_rate_decisions",
    "fct_yield_curve_daily",
    "fct_monthly_macro",
    "fct_decision_market_reaction",
)


def connect(target: str, duckdb_path: Path) -> duckdb.DuckDBPyConnection:
    if target == "prod":
        # duckdb reads MOTHERDUCK_TOKEN from the environment
        return duckdb.connect(f"md:{os.getenv('MOTHERDUCK_DATABASE', 'boe')}", read_only=True)
    if not duckdb_path.exists():
        raise SystemExit(f"{duckdb_path} not found - run `boe ingest` and `dbt build` first")
    return duckdb.connect(str(duckdb_path), read_only=True)


def export(con: duckdb.DuckDBPyConnection, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for mart in MARTS:
        path = out_dir / f"{mart}.parquet"
        con.sql(f"select * from marts.{mart}").write_parquet(str(path), compression="zstd")
        counts[mart] = con.sql(f"select count(*) from marts.{mart}").fetchone()[0]

    latest = con.sql("""
        select series_code, series_name, max(observed_on)::varchar as latest
        from staging.stg_boe__observations
        group by 1, 2
        order by 1
    """).fetchall()

    meta = {
        "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "row_counts": counts,
        "series_latest": {code: {"name": name, "latest": d} for code, name, d in latest},
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    return meta
