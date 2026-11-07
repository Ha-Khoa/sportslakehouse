"""Elo ratings as a pure function: matches in, pre-match ratings out.

Pure means: no files, no database, no clock. The same input always gives the same output, so it
can be unit-tested (tests/test_elo.py) and re-run with other parameters during tuning (week 3).
dbt calls it from the Python model dbt_project/models/gold/elo_ratings.py.

Formulas (design doc, section 9.5):
    E_home = 1 / (1 + 10 ** (-(R_home + H - R_away) / 400))
    R_home' = R_home + K * G * (S - E_home)      R_away' = R_away - K * G * (S - E_home)
    G = 1 (goal difference 0 or 1), 1.5 (2), (11 + N) / 8 (N >= 3)

Leakage rule: the value we STORE for a match is the rating BEFORE that match. The update that
the match causes is only ever used for later matches.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class EloParams:
    k: float = 20.0  # how fast ratings move after a result
    home_advantage: float = 65.0  # Elo points added to the home team when computing E_home
    initial: float = 1500.0  # start rating of teams present in the first season of the data
    promoted_start: float = 1400.0  # start rating of a team that appears for the first time later
    season_carryover: float = 0.75  # a: at a new season R = a*R + (1-a)*initial


@dataclass(frozen=True)
class MatchResult:
    match_id: str
    season: str  # "2024-25"
    match_date: date | Any  # anything sortable (date, Timestamp, ISO string)
    home_team_id: str
    away_team_id: str
    home_goals: int
    away_goals: int


@dataclass(frozen=True)
class EloRow:
    match_id: str
    team_id: str
    elo_pre: float


def expected_home_score(r_home: float, r_away: float, home_advantage: float) -> float:
    return 1.0 / (1.0 + 10 ** (-(r_home + home_advantage - r_away) / 400.0))


def goal_diff_multiplier(goal_diff: int) -> float:
    n = abs(goal_diff)
    if n <= 1:
        return 1.0
    if n == 2:
        return 1.5
    return (11 + n) / 8


def season_start_year(season: str) -> int:
    return int(season[:4])


def compute_elo(matches: Iterable[MatchResult], params: EloParams | None = None) -> list[EloRow]:
    """Return two rows per match (home and away) with the rating BEFORE the match."""
    params = params or EloParams()
    ordered = sorted(matches, key=lambda m: (m.match_date, m.match_id))
    if not ordered:
        return []
    first_year = min(season_start_year(m.season) for m in ordered)

    rating: dict[str, float] = {}
    last_year: dict[str, int] = {}

    def current(team: str, year: int) -> float:
        """Rating of `team` at the moment it plays a match in season `year`."""
        if team not in rating:
            first_time_in_first_season = year == first_year
            rating[team] = params.initial if first_time_in_first_season else params.promoted_start
            last_year[team] = year
        elif year > last_year[team]:
            # a new season for this team: pull the rating towards the mean once per elapsed season
            carry = params.season_carryover ** (year - last_year[team])
            rating[team] = carry * rating[team] + (1.0 - carry) * params.initial
            last_year[team] = year
        return rating[team]

    out: list[EloRow] = []
    for m in ordered:
        year = season_start_year(m.season)
        r_home = current(m.home_team_id, year)
        r_away = current(m.away_team_id, year)
        out.append(EloRow(m.match_id, m.home_team_id, r_home))  # stored BEFORE the update
        out.append(EloRow(m.match_id, m.away_team_id, r_away))

        if m.home_goals > m.away_goals:
            score_home = 1.0
        elif m.home_goals == m.away_goals:
            score_home = 0.5
        else:
            score_home = 0.0
        e_home = expected_home_score(r_home, r_away, params.home_advantage)
        delta = params.k * goal_diff_multiplier(m.home_goals - m.away_goals) * (score_home - e_home)
        rating[m.home_team_id] = r_home + delta
        rating[m.away_team_id] = r_away - delta
    return out
