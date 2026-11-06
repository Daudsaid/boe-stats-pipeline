.PHONY: install lint test fixtures ingest ingest-fixtures dbt dbt-fixtures build rebuild demo export app docs clean

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

ingest-fixtures:  ## offline load from tests/fixtures (into data/boe_fixtures.duckdb)
	uv run boe ingest --fixtures

dbt:              ## build models + run all dbt tests
	cd dbt && uv run dbt build

dbt-fixtures:
	cd dbt && DBT_TARGET=fixtures uv run dbt build

build: ingest dbt ## live end-to-end run (incremental after the first load)

rebuild:          ## live: drop raw tables + state, reload everything since 1975
	uv run boe ingest -v --full-refresh
	cd dbt && uv run dbt build

demo: ingest-fixtures dbt-fixtures ## offline end-to-end run (what CI does)

export:           ## write marts to app/data/*.parquet for the dashboard
	uv run boe export

app:              ## run the Streamlit dashboard locally
	uv run streamlit run app/streamlit_app.py

docs:
	cd dbt && uv run dbt docs generate && uv run dbt docs serve

clean:
	rm -rf data/*.duckdb dbt/target dbt/logs .pytest_cache
