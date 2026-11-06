.PHONY: install lint test fixtures ingest ingest-fixtures dbt build demo docs clean

export DBT_PROFILES_DIR := $(CURDIR)/dbt

install:          ## install deps + git hooks
	uv sync
	uv run pre-commit install

lint:
	uv run ruff check .
	uv run ruff format --check .

test:             ## python unit + pipeline tests
	uv run pytest -q

fixtures:         ## regenerate offline test fixtures
	uv run python scripts/make_fixtures.py

ingest:           ## pull live data from the BoE into data/boe.duckdb
	uv run boe ingest -v

ingest-fixtures:  ## offline load from tests/fixtures
	uv run boe ingest --fixtures

dbt:              ## build models + run all dbt tests
	cd dbt && uv run dbt build

build: ingest dbt ## live end-to-end run

demo: ingest-fixtures dbt ## offline end-to-end run (what CI does)

docs:
	cd dbt && uv run dbt docs generate && uv run dbt docs serve

clean:
	rm -rf data/*.duckdb dbt/target dbt/logs .pytest_cache
