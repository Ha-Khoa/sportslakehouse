.PHONY: help install bronze profile test test-data lint format all-week1 clean-cache \
	dbt-dirs dbt dbt-seed dbt-test dbt-docs validate quality-report all-week2

PYTHON ?= python
DBT ?= dbt
DBT_FLAGS = --profiles-dir . --project-dir .

help:
	@echo "make install    - install package + dev tools (editable)"
	@echo "make bronze     - download Bundesliga CSVs and write Bronze Parquet"
	@echo "make profile    - write docs/data_profile.md from Bronze"
	@echo "make test       - run unit tests (no network, no real data needed)"
	@echo "make test-data  - also run data tests against the real Bronze layer"
	@echo "make lint       - ruff check + format check"
	@echo "make format     - ruff format + autofix"
	@echo "make all-week1  - bronze + profile + test-data"
	@echo "make dbt        - dbt build: seeds, staging, Silver (Parquet) and all dbt tests"
	@echo "make dbt-test   - only the dbt tests"
	@echo "make dbt-docs   - generate dbt docs and open the lineage graph"
	@echo "make validate   - Pandera checks on Bronze and Silver"
	@echo "make quality-report - docs/quality_report.md + dbt test history (run after make dbt)"
	@echo "make all-week2  - dbt + validate + quality-report + test-data"

install:
	$(PYTHON) -m pip install -e ".[dev]"
	pre-commit install || true

bronze:
	$(PYTHON) -m sportslakehouse.ingestion.run

profile:
	$(PYTHON) -m sportslakehouse.profile

test:
	$(PYTHON) -m pytest -m "not data"

test-data:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

format:
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m ruff format .

all-week1: bronze profile test-data

clean-cache:
	rm -rf data/raw_cache

# ----------------------------------------------------------------- week 2: dbt
# dbt always runs from inside dbt_project/ (all paths in dbt_project.yml are relative to it).
dbt-dirs:
	mkdir -p data/lake/silver data/lake/gold

dbt-seed: dbt-dirs
	cd dbt_project && $(DBT) seed $(DBT_FLAGS)

dbt: dbt-dirs
	cd dbt_project && $(DBT) build $(DBT_FLAGS)

dbt-test:
	cd dbt_project && $(DBT) test $(DBT_FLAGS)

dbt-docs:
	cd dbt_project && $(DBT) docs generate $(DBT_FLAGS) && $(DBT) docs serve $(DBT_FLAGS)

validate:
	$(PYTHON) -m sportslakehouse.quality.validate

quality-report:
	$(PYTHON) -m sportslakehouse.quality.dbt_results

all-week2: dbt validate quality-report test-data
