.PHONY: help install bronze profile test test-data lint format all-week1 clean-cache

PYTHON ?= python

help:
	@echo "make install    - install package + dev tools (editable)"
	@echo "make bronze     - download Bundesliga CSVs and write Bronze Parquet"
	@echo "make profile    - write docs/data_profile.md from Bronze"
	@echo "make test       - run unit tests (no network, no real data needed)"
	@echo "make test-data  - also run data tests against the real Bronze layer"
	@echo "make lint       - ruff check + format check"
	@echo "make format     - ruff format + autofix"
	@echo "make all-week1  - bronze + profile + test-data"

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
