# Week 2 checklist, part 1 (Silver with dbt)

- [ ] `make install` (new deps: dbt-core, dbt-duckdb, pandera), then `pip freeze > requirements.lock`
- [ ] `cd dbt_project && dbt debug --profiles-dir . --project-dir .` shows "All checks passed"
- [ ] `make dbt` is green (look at the summary line: PASS / WARN / ERROR counts)
- [ ] `data/lake/silver/` contains matches, team_matches, match_odds, teams (`.parquet`)
- [ ] `make validate` prints `ok` three times
- [ ] `make test` is green
- [ ] Count: silver matches = 8028 (26 x 306 + the 2026-27 matches played so far)
- [ ] `silver.quarantine_matches` is empty (otherwise read `quarantine_reason`)
- [ ] Write down in your journal: what each singular test in `dbt_project/tests/` protects against
- [ ] Update `docs/design-decisions.md`: quarantine vs stopping the pipeline; season window July-June

# Week 2 checklist, part 2 (Gold: form, Elo, features)

- [ ] `make dbt` is green with the new Gold models (check the `elo_ratings` python model ran)
- [ ] `data/lake/gold/` contains `fct_match_features.parquet` and `elo_ratings.parquet`
- [ ] `make test` green (includes `test_elo.py`, 10 tests)
- [ ] `make test-data` green (includes `test_leakage.py`: tests 1 and 2 of the design doc)
- [ ] Run in DuckDB: `select count(*) from read_parquet('data/lake/gold/fct_match_features.parquet')` = 8028
- [ ] Open `fct_match_features` for one match and recompute `h_ppg_10` by hand from the last 10 matches
- [ ] Write in your journal: why the window ends at `1 preceding`; why Elo is a Python function
