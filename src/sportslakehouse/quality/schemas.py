"""Pandera schemas: data-quality checks on pandas DataFrames (Bronze and Silver).

Division of labour (design doc, section 8):
  * dbt tests check relations *inside the warehouse* (unique, relationships, window logic);
  * Pandera checks the *shape of a DataFrame* in Python (required columns, value ranges).
We deliberately give no dtype to columns: DuckDB, pandas 2 and pandas 3 name string/int
types differently, and we care about the values, not the dtype label.
"""

from __future__ import annotations

import pandera.pandas as pa

from sportslakehouse.config import REQUIRED_COLUMNS

RESULTS = ["H", "D", "A"]

# ----------------------------------------------------------------------------- Bronze
# Bronze is all strings and empty cells are "" (not NULL), so "required" means:
# the column exists AND its text is not empty.
_required = {
    col: pa.Column(nullable=False, checks=pa.Check.str_length(min_value=1))
    for col in REQUIRED_COLUMNS
}
_required["FTR"] = pa.Column(
    nullable=False,
    checks=[pa.Check.str_length(min_value=1), pa.Check.isin(RESULTS)],
)

bronze_matches_schema = pa.DataFrameSchema(
    {
        **_required,
        "_season": pa.Column(nullable=False, checks=pa.Check.str_matches(r"^\d{4}-\d{2}$")),
        "_file_hash": pa.Column(nullable=False, checks=pa.Check.str_length(min_value=64)),
    },
    strict=False,  # extra columns (odds, shots, ...) are allowed; their set changes per season
)

# ----------------------------------------------------------------------------- Silver
silver_matches_schema = pa.DataFrameSchema(
    {
        "match_id": pa.Column(nullable=False, unique=True),
        "season": pa.Column(nullable=False, checks=pa.Check.str_matches(r"^\d{4}-\d{2}$")),
        "match_date": pa.Column(nullable=False),
        "home_team_id": pa.Column(nullable=False),
        "away_team_id": pa.Column(nullable=False),
        "home_goals": pa.Column(nullable=False, checks=pa.Check.ge(0)),
        "away_goals": pa.Column(nullable=False, checks=pa.Check.ge(0)),
        "result": pa.Column(nullable=False, checks=pa.Check.isin(RESULTS)),
    },
    checks=[
        # DataFrame-level check: returns one True/False per row
        pa.Check(
            lambda df: df["home_team_id"] != df["away_team_id"],
            error="home team equals away team",
        ),
    ],
    strict=False,
)

silver_match_odds_schema = pa.DataFrameSchema(
    {
        "match_id": pa.Column(nullable=False),
        "bookmaker": pa.Column(
            nullable=False, checks=pa.Check.isin(["bet365", "pinnacle", "market_avg"])
        ),
        "odds_home": pa.Column(nullable=False, checks=pa.Check.gt(1.0)),
        "odds_draw": pa.Column(nullable=False, checks=pa.Check.gt(1.0)),
        "odds_away": pa.Column(nullable=False, checks=pa.Check.gt(1.0)),
    },
    strict=False,
)
