# Week 1 checklist (about 8.5 hours)

- [ ] Repo is outside iCloud (for example `~/Projects/sportslakehouse`), `git init`, first commit
- [ ] `git config user.email` is your real address
- [ ] `make install` works in a fresh `.venv`
- [ ] `make test` is green
- [ ] Read football-data.co.uk `notes.txt` (column meanings and data sources)
- [ ] `make bronze` finishes; every season shows `new`; no `FAILED` line
- [ ] Run `make bronze` a second time: every season shows `unchanged` (idempotency check)
- [ ] `make profile`; open `docs/data_profile.md`
- [ ] Every completed season has 306 matches; `result_mismatch` is 0 everywhere
- [ ] Note in your journal: which season first has shots (HS, HST) and which odds columns exist
- [ ] `make test-data` is green (if not, the failing test points at a real data problem: write it down)
- [ ] `docs/design-decisions.md` first draft (why all-string Bronze, why audit columns, why overwrite per season)
- [ ] `ruff` and `pre-commit` pass

## If something fails

- 403/HTML instead of CSV: the site may block the default client; check `User-Agent` in `config.py`.
- A season has a different match count: open the raw CSV in `data/raw_cache` and look for blank rows or a truncated file.
- Date parsing problems in the profile: look at `bad_dates` per season (two-digit years in old files).
