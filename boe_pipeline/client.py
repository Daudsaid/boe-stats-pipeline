"""Thin HTTP client for the Bank of England Interactive Database (IADB).

The IADB has no JSON API; it serves CSV from a query-string endpoint. When a
request is malformed or a series has no data in range, it answers HTTP 200 with
an HTML page instead of CSV, so we validate the payload, not just the status.
"""

from __future__ import annotations

import csv
import io
import logging
import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

log = logging.getLogger(__name__)

IADB_URL = "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; uk-interest-rates-pipeline/2.0; "
    "+https://github.com/Daudsaid/uk-interest-rates-pipeline)"
)
IADB_DATE_FORMAT = "%d %b %Y"  # e.g. "02 Jan 2025"


class IADBError(RuntimeError):
    """The IADB returned something other than the expected CSV."""


class TransientIADBError(IADBError):
    """Retryable failure: network error, timeout, 5xx or 429."""


@dataclass(frozen=True)
class Observation:
    series_code: str
    date: date
    value: Decimal


def _fmt_date(d: date) -> str:
    return d.strftime("%d/%b/%Y")


def build_params(series_code: str, start: date, end: date | None = None) -> dict[str, str]:
    return {
        "csv.x": "yes",
        "SeriesCodes": series_code,
        "Datefrom": _fmt_date(start),
        "Dateto": _fmt_date(end) if end else "now",
        "CSVF": "TN",  # tabular, no titles
        "UsingCodes": "Y",
        "VPD": "Y",
        "VFD": "N",
    }


def parse_csv(text: str, series_code: str) -> Iterator[Observation]:
    """Parse an IADB CSV payload into observations.

    Expected shape::

        DATE,IUDBEDR
        02 Jan 2025,4.75
    """
    stripped = text.lstrip()
    if not stripped or stripped.startswith("<"):
        raise IADBError(
            f"{series_code}: expected CSV, got HTML or empty body "
            f"(series code wrong, no data in range, or request blocked)"
        )

    reader = csv.reader(io.StringIO(stripped))
    header = [h.strip().upper() for h in next(reader)]
    if len(header) < 2 or header[0] != "DATE" or header[1] != series_code.upper():
        raise IADBError(f"{series_code}: unexpected CSV header {header}")

    for line_no, row in enumerate(reader, start=2):
        if not row or not row[0].strip():
            continue
        raw_value = row[1].strip() if len(row) > 1 else ""
        if raw_value in {"", "n/a", "N/A", ".."}:
            continue  # IADB leaves gaps blank on non-publication days
        try:
            obs_date = datetime.strptime(row[0].strip(), IADB_DATE_FORMAT).date()
            value = Decimal(raw_value)
        except (ValueError, InvalidOperation) as exc:
            raise IADBError(f"{series_code}: bad row {line_no}: {row!r}") from exc
        yield Observation(series_code=series_code, date=obs_date, value=value)


class IADBClient:
    def __init__(self, session: requests.Session | None = None, timeout: float = 30.0):
        self.session = session or requests.Session()
        # requests always sets its own default UA, so overwrite rather than setdefault
        self.session.headers["User-Agent"] = os.getenv("BOE_USER_AGENT", DEFAULT_USER_AGENT)
        self.timeout = timeout

    @retry(
        retry=retry_if_exception_type(TransientIADBError),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=2, max=60),
        reraise=True,
    )
    def _get(self, params: dict[str, str]) -> str:
        try:
            resp = self.session.get(IADB_URL, params=params, timeout=self.timeout)
        except (requests.ConnectionError, requests.Timeout) as exc:
            raise TransientIADBError(str(exc)) from exc
        if resp.status_code == 429 or resp.status_code >= 500:
            raise TransientIADBError(f"HTTP {resp.status_code}")
        if resp.status_code >= 400:
            raise IADBError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        return resp.text

    def fetch(self, series_code: str, start: date, end: date | None = None) -> list[Observation]:
        text = self._get(build_params(series_code, start, end))
        rows = list(parse_csv(text, series_code))
        log.info("fetched %s rows for %s from %s", len(rows), series_code, start)
        return rows
