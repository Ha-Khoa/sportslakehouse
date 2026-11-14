"""Known real-world results as a regression check on Silver + Gold (marker: data).

These are the "compare with the real league table" step of week 2, automated. The values were
computed from the football-data.co.uk CSVs; confirm them yourself against an independent
source (for example the official Bundesliga site) once, then keep the test.
"""

from pathlib import Path

import duckdb
import pytest

from sportslakehouse.config import Settings

pytestmark = pytest.mark.data


@pytest.fixture(scope="module")
def con():
    s = Settings()
    standings = s.gold_dir / "mart_standings.parquet"
    streaks = s.gold_dir / "mart_unbeaten_streaks.parquet"
    home_away = s.gold_dir / "mart_home_away_by_season.parquet"
    missing = [p for p in (standings, streaks, home_away) if not Path(p).exists()]
    if missing:
        pytest.skip("Gold marts missing: run `make dbt` first")
    c = duckdb.connect()
    c.execute(f"create view standings as select * from read_parquet('{standings}')")
    c.execute(f"create view streaks as select * from read_parquet('{streaks}')")
    c.execute(f"create view home_away as select * from read_parquet('{home_away}')")
    yield c
    c.close()


def _final(con, season, team_id):
    return con.execute(
        "select points, wins, draws, losses, goals_for, goals_against from standings "
        "where season = ? and matches_played = 34 and team_id = ?",
        [season, team_id],
    ).fetchone()


def test_leverkusen_2023_24_unbeaten_champions(con):
    assert _final(con, "2023-24", "bayer-04-leverkusen") == (90, 28, 6, 0, 89, 24)
    champion = con.execute(
        "select team_id from standings "
        "where season = '2023-24' and matches_played = 34 and rank = 1"
    ).fetchone()[0]
    assert champion == "bayer-04-leverkusen"


def test_bayern_2012_13_record_points(con):
    assert _final(con, "2012-13", "bayern-muenchen") == (91, 29, 4, 1, 98, 18)


def test_every_completed_season_has_18_teams_in_the_final_table(con):
    bad = con.execute(
        "select season, count(*) from standings where matches_played = 34 "
        "group by season having count(*) <> 18"
    ).fetchall()
    assert not bad, bad


def test_longest_unbeaten_run_in_a_season_is_leverkusens_34(con):
    team, season, length = con.execute(
        "select team_id, season, streak_length from streaks order by streak_length desc limit 1"
    ).fetchone()
    assert (team, season, length) == ("bayer-04-leverkusen", "2023-24", 34)


def test_home_win_rate_in_the_covid_season_is_lower(con):
    rates = dict(con.execute("select season, home_win_rate from home_away").fetchall())
    assert round(rates["2019-20"], 3) == 0.402
    assert round(rates["2024-25"], 3) == 0.386
    assert rates["2019-20"] < rates["2018-19"]
