"""Offline fetcher that serves IADB-shaped CSVs from disk.

Used by tests and CI so the full pipeline (dlt + dbt) runs without network
access. It goes through the same ``parse_csv`` as the live client, so fixture
files must match the real IADB format.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from boe_pipeline.client import Observation, parse_csv

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "iadb"


class FixtureFetcher:
    def __init__(self, directory: Path = FIXTURES_DIR):
        self.directory = directory

    def fetch(self, series_code: str, start: date, end: date | None = None) -> list[Observation]:
        text = (self.directory / f"{series_code}.csv").read_text()
        return [
            o
            for o in parse_csv(text, series_code)
            if o.date >= start and (end is None or o.date <= end)
        ]
