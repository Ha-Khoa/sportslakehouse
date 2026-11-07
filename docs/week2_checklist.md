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
