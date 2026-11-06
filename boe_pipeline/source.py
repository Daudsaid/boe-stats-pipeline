"""dlt source for Bank of England IADB series.

Loading strategy
----------------
* ``observations`` is a long table keyed on (series_code, date) and loaded with
  ``merge`` so re-fetched rows upsert instead of duplicating.
* Each series keeps its own high-water mark in dlt state. On every run we
  re-fetch a lookback window behind that mark, because the BoE revises recent
  data (monthly money statistics especially). Merge makes this idempotent.
* ``series`` is the registry itself, replaced every run, so metadata lives in
  the warehouse next to the data it describes.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from datetime import date, timedelta
from typing import Protocol

import dlt

from boe_pipeline.client import IADBClient, Observation
from boe_pipeline.series import Series, get_series

DEFAULT_START = date(1975, 1, 1)
LOOKBACK_DAYS = {"daily": 14, "monthly": 400}


class Fetcher(Protocol):
    def fetch(
        self, series_code: str, start: date, end: date | None = None
    ) -> list[Observation]: ...


def _start_for(series: Series, last_date: str | None, initial: date) -> date:
    if last_date is None:
        return initial
    lookback = timedelta(days=LOOKBACK_DAYS[series.frequency])
    return max(initial, date.fromisoformat(last_date) - lookback)


@dlt.source(name="boe")
def boe_source(
    series_codes: list[str] | None = None,
    start_date: date = DEFAULT_START,
    end_date: date | None = None,
    fetcher: Fetcher | None = None,
) -> Iterable:
    selected = get_series(series_codes)
    client = fetcher or IADBClient()

    @dlt.resource(name="series", write_disposition="replace", primary_key="code")
    def series_resource() -> Iterator[dict]:
        yield from (s.as_row() for s in selected)

    @dlt.resource(
        name="observations",
        write_disposition="merge",
        primary_key=("series_code", "date"),
        columns={
            "series_code": {"data_type": "text", "nullable": False},
            "date": {"data_type": "date", "nullable": False},
            "value": {"data_type": "decimal", "precision": 20, "scale": 6, "nullable": False},
        },
    )
    def observations() -> Iterator[list[dict]]:
        state = dlt.current.resource_state().setdefault("last_date", {})
        for s in selected:
            start = _start_for(s, state.get(s.code), start_date)
            rows = client.fetch(s.code, start, end_date)
            if not rows:
                continue
            yield [{"series_code": o.series_code, "date": o.date, "value": o.value} for o in rows]
            # Advance the mark only after the batch was handed to dlt.
            state[s.code] = max(o.date for o in rows).isoformat()

    return series_resource, observations
