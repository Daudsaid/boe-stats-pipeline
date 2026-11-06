"""End-to-end dlt tests against a throwaway DuckDB file, fully offline."""

from datetime import date

import dlt
import duckdb
import pytest

from boe_pipeline.client import Observation
from boe_pipeline.fixtures import FixtureFetcher
from boe_pipeline.series import SERIES, get_series
from boe_pipeline.source import LOOKBACK_DAYS, boe_source


class RecordingFetcher(FixtureFetcher):
    """Fixture fetcher that remembers which start date was requested per series."""

    def __init__(self):
        super().__init__()
        self.calls: dict[str, date] = {}

    def fetch(self, series_code, start, end=None) -> list[Observation]:
        self.calls[series_code] = start
        return super().fetch(series_code, start, end)


@pytest.fixture
def pipeline(tmp_path):
    return dlt.pipeline(
        pipeline_name="boe_test",
        pipelines_dir=str(tmp_path / "pipelines"),
        destination=dlt.destinations.duckdb(str(tmp_path / "test.duckdb")),
        dataset_name="raw_boe",
    )


def _query(pipeline, sql):
    with duckdb.connect(pipeline.destination.config_params["credentials"], read_only=True) as con:
        return con.sql(sql).fetchall()


def _count(pipeline):
    return _query(pipeline, "select count(*) from raw_boe.observations")[0][0]


def test_registry_codes_and_names_are_unique():
    assert len({s.code for s in SERIES}) == len(SERIES)
    assert len({s.name for s in SERIES}) == len(SERIES)


def test_get_series_rejects_unknown_codes():
    with pytest.raises(ValueError, match="NOPE"):
        get_series(["IUDBEDR", "NOPE"])


def test_full_load_writes_every_series(pipeline):
    pipeline.run(boe_source(fetcher=FixtureFetcher())).raise_on_failed_jobs()
    rows = _query(pipeline, "select distinct series_code from raw_boe.observations")
    codes = {r[0] for r in rows}
    assert codes == {s.code for s in SERIES}
    assert _query(pipeline, "select count(*) from raw_boe.series")[0][0] == len(SERIES)


def test_rerun_is_idempotent(pipeline):
    pipeline.run(boe_source(fetcher=FixtureFetcher())).raise_on_failed_jobs()
    first = _count(pipeline)
    pipeline.run(boe_source(fetcher=FixtureFetcher())).raise_on_failed_jobs()
    assert _count(pipeline) == first
    dupes = _query(
        pipeline,
        """
        select count(*) from (
            select series_code, date from raw_boe.observations group by 1, 2 having count(*) > 1
        )""",
    )[0][0]
    assert dupes == 0


def test_incremental_run_refetches_only_lookback_window(pipeline):
    pipeline.run(boe_source(series_codes=["IUDBEDR", "IUMBV34"], fetcher=FixtureFetcher()))

    fetcher = RecordingFetcher()
    pipeline.run(boe_source(series_codes=["IUDBEDR", "IUMBV34"], fetcher=fetcher))

    # fixtures end on 2025-12-31 for both series
    assert fetcher.calls["IUDBEDR"] == date(2025, 12, 31) - _days(LOOKBACK_DAYS["daily"])
    assert fetcher.calls["IUMBV34"] == date(2025, 12, 31) - _days(LOOKBACK_DAYS["monthly"])


def test_revised_values_overwrite_previous_load(pipeline):
    pipeline.run(boe_source(series_codes=["IUMBV34"], fetcher=FixtureFetcher()))

    class Revised(FixtureFetcher):
        def fetch(self, series_code, start, end=None):
            rows = super().fetch(series_code, start, end)
            last = rows[-1]
            return rows[:-1] + [Observation(last.series_code, last.date, last.value + 1)]

    before = _query(pipeline, "select value from raw_boe.observations where date = '2025-12-31'")
    pipeline.run(boe_source(series_codes=["IUMBV34"], fetcher=Revised()))
    after = _query(pipeline, "select value from raw_boe.observations where date = '2025-12-31'")

    assert len(after) == 1
    assert after[0][0] == before[0][0] + 1


def _days(n):
    from datetime import timedelta

    return timedelta(days=n)
