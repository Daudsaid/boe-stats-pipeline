"""Command-line entry point: ``boe ingest`` / ``uv run boe ingest --help``."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date
from pathlib import Path

import dlt

from boe_pipeline.source import DEFAULT_START, boe_source

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DUCKDB_PATH = PROJECT_ROOT / "data" / "boe.duckdb"
# Synthetic fixtures get their own file AND pipeline name, so fake rows and
# fixture high-water marks can never leak into the real warehouse.
FIXTURES_DUCKDB_PATH = PROJECT_ROOT / "data" / "boe_fixtures.duckdb"
DATASET = "raw_boe"


def make_destination(target: str):
    """dev -> local DuckDB file; prod -> MotherDuck (needs MOTHERDUCK_TOKEN);
    fixtures -> separate local DuckDB file."""
    if target == "prod":
        token = os.getenv("MOTHERDUCK_TOKEN")
        if not token:
            sys.exit("MOTHERDUCK_TOKEN is not set; required for --target prod")
        return dlt.destinations.motherduck(
            credentials={"database": os.getenv("MOTHERDUCK_DATABASE", "boe"), "password": token}
        )
    if target == "fixtures":
        path = Path(os.getenv("BOE_FIXTURES_DUCKDB_PATH", FIXTURES_DUCKDB_PATH))
    else:
        path = Path(os.getenv("BOE_DUCKDB_PATH", DEFAULT_DUCKDB_PATH))
    path.parent.mkdir(parents=True, exist_ok=True)
    return dlt.destinations.duckdb(str(path))


def ingest(args: argparse.Namespace) -> None:
    fetcher = None
    target = args.target
    refresh = "drop_sources" if args.full_refresh else None
    if args.fixtures:
        if target == "prod":
            sys.exit("--fixtures cannot be combined with --target prod")
        from boe_pipeline.fixtures import FixtureFetcher

        fetcher = FixtureFetcher()
        target = "fixtures"
        refresh = "drop_sources"  # fixtures are static: always rebuild from scratch

    pipeline = dlt.pipeline(
        pipeline_name=f"boe_{target}",
        destination=make_destination(target),
        dataset_name=DATASET,
        progress="log" if args.verbose else None,
    )
    source = boe_source(
        series_codes=args.series or None,
        start_date=args.start,
        fetcher=fetcher,
    )
    info = pipeline.run(source, refresh=refresh)
    print(info)
    info.raise_on_failed_jobs()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="boe", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ingest", help="Extract BoE series and load them into the warehouse")
    p.add_argument("--target", choices=["dev", "prod"], default="dev")
    p.add_argument("--series", nargs="*", help="Only these series codes (default: all)")
    p.add_argument(
        "--start",
        type=date.fromisoformat,
        default=DEFAULT_START,
        help="Earliest date for a first load (YYYY-MM-DD)",
    )
    p.add_argument(
        "--full-refresh",
        action="store_true",
        help="Drop loaded tables + state and reload from --start",
    )
    p.add_argument(
        "--fixtures",
        action="store_true",
        help="Read tests/fixtures instead of calling the BoE (offline/CI)",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(func=ingest)

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    args.func(args)


if __name__ == "__main__":
    main()
