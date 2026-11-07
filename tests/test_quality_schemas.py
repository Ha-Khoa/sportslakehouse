"""Unit tests for the Pandera schemas, using tiny hand-made DataFrames (no real data)."""

import pandas as pd
import pandera.pandas as pa
import pytest

from sportslakehouse.quality.schemas import (
    bronze_matches_schema,
    silver_match_odds_schema,
    silver_matches_schema,
)


def _silver_ok() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "match_id": ["a", "b"],
            "season": ["2024-25", "2024-25"],
            "match_date": pd.to_datetime(["2024-08-23", "2024-08-24"]),
            "home_team_id": ["x", "y"],
            "away_team_id": ["y", "z"],
            "home_goals": [2, 0],
            "away_goals": [3, 0],
            "result": ["A", "D"],
        }
    )


def test_silver_matches_valid_frame_passes():
    silver_matches_schema.validate(_silver_ok(), lazy=True)


@pytest.mark.parametrize(
    ("column", "value"),
    [("result", "X"), ("home_goals", -1), ("season", "2024"), ("home_team_id", None)],
)
def test_silver_matches_rejects_bad_values(column, value):
    df = _silver_ok()
    df.loc[0, column] = value
    with pytest.raises(pa.errors.SchemaErrors):
        silver_matches_schema.validate(df, lazy=True)


def test_silver_matches_rejects_same_team_on_both_sides():
    df = _silver_ok()
    df.loc[0, "away_team_id"] = df.loc[0, "home_team_id"]
    with pytest.raises(pa.errors.SchemaErrors):
        silver_matches_schema.validate(df, lazy=True)


def test_silver_matches_rejects_duplicate_match_id():
    df = _silver_ok()
    df.loc[1, "match_id"] = "a"
    with pytest.raises(pa.errors.SchemaErrors):
        silver_matches_schema.validate(df, lazy=True)


def test_odds_must_be_greater_than_one():
    df = pd.DataFrame(
        {
            "match_id": ["a"],
            "bookmaker": ["bet365"],
            "odds_home": [1.0],
            "odds_draw": [3.2],
            "odds_away": [4.0],
        }
    )
    with pytest.raises(pa.errors.SchemaErrors):
        silver_match_odds_schema.validate(df, lazy=True)


def _bronze_ok() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": ["23/08/2024"],
            "HomeTeam": ["M'gladbach"],
            "AwayTeam": ["Leverkusen"],
            "FTHG": ["2"],
            "FTAG": ["3"],
            "FTR": ["A"],
            "_season": ["2024-25"],
            "_file_hash": ["f" * 64],
        }
    )


def test_bronze_valid_frame_passes():
    bronze_matches_schema.validate(_bronze_ok(), lazy=True)


def test_bronze_missing_required_column_fails():
    with pytest.raises(pa.errors.SchemaErrors):
        bronze_matches_schema.validate(_bronze_ok().drop(columns=["FTAG"]), lazy=True)


def test_bronze_empty_string_counts_as_missing():
    df = _bronze_ok()
    df.loc[0, "HomeTeam"] = ""  # Bronze stores empty cells as "", not NULL
    with pytest.raises(pa.errors.SchemaErrors):
        bronze_matches_schema.validate(df, lazy=True)
