# Design decisions

Why the project is built the way it is. One entry per decision: context, decision, consequence.
Week 1 covers the Bronze layer only. Numbers marked **(verify)** must be re-checked against
`docs/data_profile.md` after the final `make bronze` run.

## D1. Bronze stores every column as a string

- **Context.** The CSV files differ from season to season (columns appear and disappear, cells
  are empty, dates have two- or four-digit years). Letting a parser infer types breaks as soon as
  a blank cell or an unexpected value shows up.
- **Decision.** Bronze keeps the source exactly as delivered: all columns are strings and no value
  is converted. Only structural clean-up is allowed (strip whitespace, drop empty rows and unnamed
  trailing columns). Types, team names and dates are handled in Silver.
- **Consequence.** Bronze can always be re-read and re-interpreted without downloading again.
  Every typing mistake is a Silver bug that can be fixed without touching the raw layer.

## D2. Audit columns on every row

- **Decision.** Each Bronze row carries `_season`, `_league`, `_source_url`, `_file_hash`,
  `_ingested_at` and `_row_number`.
- **Why.** Any number in a later layer can be traced back to the exact file (SHA-256), the URL it
  came from, the moment it was loaded and its position in the file.

## D3. One Parquet partition per season, overwritten on each run

- **Decision.** `data/lake/bronze/football_data/season=YYYY-YY/D1.parquet`, rewritten as a whole
  through a temporary file and an atomic rename.
- **Why.** Running the pipeline twice must give the same result (idempotency). Appending would
  duplicate rows; overwriting one partition cannot. The atomic rename means a crash never leaves a
  half-written file.

## D4. Skip logic: file hash AND parser version

- **Context.** The first version skipped a season when the SHA-256 of the CSV matched the last
  logged hash. After I fixed a parsing bug (see D5), the pipeline still reported `unchanged`
  and kept the wrong Parquet files, because the *input* had not changed, only the *code*.
- **Decision.** A season is skipped only if the file hash is unchanged **and** the parser version
  recorded in the ingestion log equals the current `CLEAN_VERSION`. Any change to the cleaning
  logic bumps that version and forces a rebuild from the raw cache (no download needed).
- **Lesson.** Idempotency is about (input, code) together, not just the input.

## D5. The `csv` module instead of `pandas.read_csv` for the first parse step

- **Incident.** The first Bronze run produced 290 matches for 2002-03 and 194 for 2003-04
  (expected 306). I first assumed the source was incomplete. Checking the raw files showed that
  both contain 306 matches and every team plays 34 games.
- **Root cause.** The raw files are *ragged*: some rows have more comma-separated fields than the
  header (extra empty cells at the end). `pandas.read_csv(..., on_bad_lines="warn")` skips such
  rows and only prints a warning. 16 rows were lost in 2002-03 and 112 in 2003-04, silently.
- **Decision.** Parse with the standard `csv` module, pad or trim rows to the header width, and
  raise `SchemaError` if a row has a non-empty value beyond the named columns, so real data is
  never dropped quietly.
- **Safeguards.** (1) a unit test with a ragged row; (2) a data test that compares the Bronze row
  count with the number of non-empty rows in the raw CSV; (3) a test that every completed season
  has exactly 306 matches (no exceptions list).
- **Lesson.** A test that is changed to accept a surprising number hides the bug. First find out
  *why* the number is surprising.

## D6. Schema drift is recorded, not assumed away

- **Decision.** `column_inventory.parquet` stores, per season and column, the share of empty
  cells. Seasons are combined by column name (`union_by_name`), so a missing column becomes NULL.
- **What the data shows (share of filled cells in the raw CSVs).**

| Group | Available | Gaps |
|---|---|---|
| Shots `HS`, `AS` | 2000-01 to 2001-02, 2003-04 onward | missing in 2002-03 |
| Shots on target `HST`, `AST` | 2000-01 to 2001-02, 2006-07 onward | missing 2002-03 to 2005-06 |
| Bet365 opening `B365H/D/A` | 2002-03 onward | none after that |
| Pinnacle `PS*`, `PSC*` | 2012-13 to 2024-25 | only about 49% filled in 2025-26, absent in 2026-27 |
| Bet365 closing `B365C*` | 2019-20 onward | |
| Market average `Avg*`, `AvgC*` | 2019-20 onward | |

**(verify against the inventory after the rebuild)**

## D7. Choice of reference odds (decision for the baseline B3)

- **Problem.** No single bookmaker column covers all seasons, and the Pinnacle closing odds,
  the usual gold standard, are incomplete exactly in the most recent seasons that I plan to use
  as holdout (2024-25, 2025-26).
- **Decision (to confirm in week 3).** Use the market-average closing odds (`AvgC*`) from 2019-20
  onward and Bet365 opening odds (`B365*`) for earlier seasons. Evaluate B3 only on seasons where the
  chosen column is at least 95% filled, and state the column per season in the README.
- **Why.** The comparison with the bookmaker is the central claim of the project, so the baseline
  must be defined by the data that really exists, not by the column I would like to have.

## D8. Date handling in the profile

- **Problem.** Old files use `dd/mm/yy`, new ones `dd/mm/yyyy`. Trying `%d/%m/%Y` first on
  `25/08/00` can silently produce the year 0000 instead of failing.
- **Decision.** Choose the format by string length (10 characters or 8 characters), and count a
  date before 1990 as invalid. The profile reports `bad_dates` per season.

## Known limitations of the data (so far)

- Match kick-off times are not available for all seasons, so same-day order is defined by
  `(match_date, match_id)`.
- The current season (2026-27) is in progress and is re-downloaded on every run because the
  source corrects results and adds odds late.

## Open questions for week 2

- Team-name mapping: how many distinct names exist across 27 seasons, and which ones change?
- Which key identifies a match: `(match_date, home_team, away_team)` is unique per the data test.
