# SportsLakehouse

Bundesliga data platform: medallion lakehouse (Parquet, DuckDB, dbt), match-outcome forecasting
evaluated against bookmaker odds, MLOps, REST API and dashboard.

> Status: **week 1** (Bronze layer and data profiling). The rest follows the design document.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
cp .env.example .env
make install
make test          # unit tests, no network needed
make bronze        # download 2000-01 ... current season, write Bronze Parquet
make profile       # writes docs/data_profile.md
make test-data     # data tests against the real Bronze layer
```

## What week 1 does

| Step | Module | Result |
|---|---|---|
| Download CSV per season (cache, retry, atomic write, SHA-256) | `ingestion/football_data.py` | `data/raw_cache/` |
| Structural clean-up only (all columns stay strings) | `clean_raw_csv` | no value is changed |
| Audit columns | `add_audit_columns` | `_season`, `_source_url`, `_file_hash`, ... |
| One Parquet partition per season, overwritten idempotently | `write_bronze` | `data/lake/bronze/football_data/season=YYYY-YY/` |
| Which columns exist in which season | `ingestion/inventory.py` | `column_inventory.parquet` |
| Data profile report | `profile.py` | `docs/data_profile.md` |

## Data

Match results and odds come from [football-data.co.uk](https://football-data.co.uk). Read their
`notes.txt` and terms before publishing anything derived from it. The raw data is not stored in
this repository; `make bronze` downloads it.
https://football-data.co.uk/notes.txt 

This project is for educational and analytical purposes only and does not provide betting advice.
