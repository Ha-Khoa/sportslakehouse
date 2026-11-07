"""Elo rating of each team BEFORE each match (gold.elo_ratings), grain (match_id, team_id).

Elo depends on the previous result of the same team, so it is a sequential calculation that
SQL window functions cannot express cleanly. It is therefore a dbt Python model: dbt gives us
the Silver matches as a table, we call the pure function in sportslakehouse.features.elo, and
dbt stores the returned DataFrame. Tuning K, H and the carry-over happens in week 3 (on the
development seasons only); until then the defaults of EloParams are used.
"""

import pandas as pd

from sportslakehouse.features.elo import EloParams, MatchResult, compute_elo


def model(dbt, session):
    dbt.config(materialized="table")

    matches = dbt.ref("silver_matches").df()
    results = [
        MatchResult(
            match_id=r.match_id,
            season=r.season,
            match_date=r.match_date,
            home_team_id=r.home_team_id,
            away_team_id=r.away_team_id,
            home_goals=int(r.home_goals),
            away_goals=int(r.away_goals),
        )
        for r in matches.itertuples(index=False)
    ]
    rows = compute_elo(results, EloParams())
    return pd.DataFrame(
        {
            "match_id": [r.match_id for r in rows],
            "team_id": [r.team_id for r in rows],
            "elo_pre": [r.elo_pre for r in rows],
        }
    )
