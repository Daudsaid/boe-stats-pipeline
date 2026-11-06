"""Smoke test: the Streamlit app renders every tab without errors on fixture data."""

import shutil
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def app_copy(tmp_path_factory):
    """Copy the app next to freshly exported *fixture* marts (never the real ones)."""
    tmp = tmp_path_factory.mktemp("app")
    shutil.copy(ROOT / "app" / "streamlit_app.py", tmp / "streamlit_app.py")
    db = tmp / "fixtures.duckdb"
    env = {
        **__import__("os").environ,
        "BOE_FIXTURES_DUCKDB_PATH": str(db),
        "DLT_DATA_DIR": str(tmp / "dlt"),
    }
    run = lambda *cmd: subprocess.run(cmd, check=True, env=env, cwd=ROOT)  # noqa: E731
    run("boe", "ingest", "--fixtures")
    run(
        "dbt",
        "build",
        "--quiet",
        "--target",
        "fixtures",
        "--project-dir",
        "dbt",
        "--profiles-dir",
        "dbt",
    )
    run("boe", "export", "--target", "fixtures", "--out", str(tmp / "data"))
    return tmp / "streamlit_app.py"


def test_app_renders_without_exceptions(app_copy):
    at = AppTest.from_file(str(app_copy), default_timeout=60).run()
    assert not at.exception
    assert [m.label for m in at.metric][:5] == [
        "Bank Rate",
        "10y gilt yield",
        "2y fixed mortgage (75% LTV)",
        "GBP/USD",
        "M4 money growth (12m)",
    ]
    assert len(at.tabs) == 5


def test_app_survives_extreme_year_ranges(app_copy):
    at = AppTest.from_file(str(app_copy), default_timeout=60).run()
    for slider in at.slider:
        slider.set_value((slider.max, slider.max)).run()
        assert not at.exception
