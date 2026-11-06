"""The CLI must keep synthetic fixtures out of the real warehouse."""

import duckdb
import pytest

from boe_pipeline import cli


@pytest.fixture
def paths(tmp_path, monkeypatch):
    real = tmp_path / "boe.duckdb"
    fake = tmp_path / "boe_fixtures.duckdb"
    monkeypatch.setenv("BOE_DUCKDB_PATH", str(real))
    monkeypatch.setenv("BOE_FIXTURES_DUCKDB_PATH", str(fake))
    monkeypatch.setenv("DLT_DATA_DIR", str(tmp_path / "dlt"))
    monkeypatch.setenv("HOME", str(tmp_path))
    return real, fake


def test_fixture_ingest_never_touches_the_real_warehouse(paths):
    real, fake = paths
    cli.main(["ingest", "--fixtures"])
    assert fake.exists()
    assert not real.exists()


def test_fixture_ingest_always_rebuilds_from_scratch(paths):
    _, fake = paths
    cli.main(["ingest", "--fixtures"])
    cli.main(["ingest", "--fixtures"])
    with duckdb.connect(str(fake), read_only=True) as con:
        loads = con.sql("select count(distinct _dlt_load_id) from raw_boe.observations").fetchone()
    assert loads == (1,)  # second run replaced the first instead of merging into it


def test_fixtures_refuse_prod_target(paths):
    with pytest.raises(SystemExit, match="cannot be combined"):
        cli.main(["ingest", "--fixtures", "--target", "prod"])


def test_export_writes_every_mart_and_metadata(paths, tmp_path, monkeypatch):
    import json
    import subprocess

    from boe_pipeline.export import MARTS

    _, fake = paths
    cli.main(["ingest", "--fixtures"])
    root = cli.PROJECT_ROOT
    subprocess.run(
        [
            "dbt",
            "build",
            "--target",
            "fixtures",
            "--profiles-dir",
            str(root / "dbt"),
            "--project-dir",
            str(root / "dbt"),
            "--quiet",
        ],
        check=True,
        env={**__import__("os").environ, "BOE_FIXTURES_DUCKDB_PATH": str(fake)},
    )
    out = tmp_path / "export"
    cli.main(["export", "--target", "fixtures", "--out", str(out)])

    for mart in MARTS:
        assert (out / f"{mart}.parquet").stat().st_size > 0
    meta = json.loads((out / "meta.json").read_text())
    assert meta["row_counts"]["fct_bank_rate_decisions"] == 6
    assert meta["series_latest"]["IUDBEDR"]["latest"] == "2025-12-31"
