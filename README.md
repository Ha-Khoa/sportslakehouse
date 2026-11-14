# SportsLakehouse

Bundesliga data platform: medallion lakehouse (Parquet, DuckDB, dbt), match-outcome forecasting
evaluated against bookmaker odds, MLOps, REST API and dashboard.

> Status: **week 2** (Silver and Gold layers with dbt, data-quality tests, Elo and rolling features).
> The rest follows the design document.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
cp .env.example .env
make install
make test          # unit tests, no network needed
make bronze        # download 2000-01 ... current season, write Bronze Parquet
make profile       # writes docs/data_profile.md
make test-data     # data tests against the real Bronze layer
make dbt           # dbt build: Silver + Gold (Parquet in data/lake/) and all dbt tests
make validate      # Pandera checks on Bronze and Silver
make quality-report  # docs/quality_report.md from the last dbt run
make dbt-docs      # dbt docs with the lineage graph
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

## What week 2 adds

| Layer | Models | Notes |
|---|---|---|
| Staging | `stg_fd_matches` | rename + cast only; Bronze stays all-string |
| Silver | `matches`, `team_matches` (2 rows per match), `match_odds` (long), `teams`, `quarantine_matches` | row-level defects go to quarantine, structural defects stop the build |
| Gold | `elo_ratings` (Python model), `fct_match_features`, `mart_standings`, `mart_team_form`, `mart_unbeaten_streaks`, `mart_home_away_by_season` | features use windows that end at `1 PRECEDING`; leakage tests in `tests/test_leakage.py` |

## Data

Match results and odds come from [football-data.co.uk](https://football-data.co.uk). Read their
`notes.txt` and terms before publishing anything derived from it. The raw data is not stored in
this repository; `make bronze` downloads it.
https://football-data.co.uk/notes.txt 

This project is for educational and analytical purposes only and does not provide betting advice.
