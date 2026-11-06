from datetime import date
from decimal import Decimal

import pytest
import responses

from boe_pipeline.client import (
    IADB_URL,
    IADBClient,
    IADBError,
    TransientIADBError,
    build_params,
    parse_csv,
)


def test_build_params_formats_dates_the_way_iadb_expects():
    params = build_params("IUDBEDR", date(2025, 1, 2))
    assert params["Datefrom"] == "02/Jan/2025"
    assert params["Dateto"] == "now"
    assert params["SeriesCodes"] == "IUDBEDR"
    assert build_params("IUDBEDR", date(2025, 1, 2), date(2025, 3, 31))["Dateto"] == "31/Mar/2025"


def test_parse_csv_reads_values_as_exact_decimals():
    rows = list(parse_csv("DATE,IUDBEDR\n02 Jan 2025,4.75\n03 Jan 2025,4.7500\n", "IUDBEDR"))
    assert [(r.date, r.value) for r in rows] == [
        (date(2025, 1, 2), Decimal("4.75")),
        (date(2025, 1, 3), Decimal("4.7500")),
    ]


def test_parse_csv_skips_blank_values_and_lines():
    text = "DATE,XUDLUSS\n02 Jan 2025,1.2500\n03 Jan 2025,\n\n06 Jan 2025,1.2600\n"
    assert [r.date.day for r in parse_csv(text, "XUDLUSS")] == [2, 6]


@pytest.mark.parametrize("body", ["", "<html><body>No data</body></html>", "  \n<!DOCTYPE html>"])
def test_parse_csv_rejects_html_and_empty_bodies(body):
    with pytest.raises(IADBError, match="expected CSV"):
        list(parse_csv(body, "IUDBEDR"))


def test_parse_csv_rejects_header_for_a_different_series():
    with pytest.raises(IADBError, match="unexpected CSV header"):
        list(parse_csv("DATE,IUDSOIA\n02 Jan 2025,4.7\n", "IUDBEDR"))


def test_parse_csv_rejects_malformed_rows():
    with pytest.raises(IADBError, match="bad row 2"):
        list(parse_csv("DATE,IUDBEDR\n2025-01-02,4.75\n", "IUDBEDR"))


@responses.activate
def test_client_retries_transient_errors_then_succeeds(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)  # skip tenacity backoff
    responses.get(IADB_URL, status=503)
    responses.get(IADB_URL, status=429)
    responses.get(IADB_URL, body="DATE,IUDBEDR\n02 Jan 2025,4.75\n")

    rows = IADBClient().fetch("IUDBEDR", date(2025, 1, 1))

    assert len(rows) == 1
    assert len(responses.calls) == 3


@responses.activate
def test_client_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    responses.get(IADB_URL, status=500)
    with pytest.raises(TransientIADBError):
        IADBClient().fetch("IUDBEDR", date(2025, 1, 1))
    assert len(responses.calls) == 5


@responses.activate
def test_client_does_not_retry_client_errors():
    responses.get(IADB_URL, status=404, body="not found")
    with pytest.raises(IADBError, match="HTTP 404"):
        IADBClient().fetch("IUDBEDR", date(2025, 1, 1))
    assert len(responses.calls) == 1


@responses.activate
def test_client_sends_identifying_user_agent():
    responses.get(IADB_URL, body="DATE,IUDBEDR\n02 Jan 2025,4.75\n")
    IADBClient().fetch("IUDBEDR", date(2025, 1, 1))
    assert "boe-stats-pipeline" in responses.calls[0].request.headers["User-Agent"]
