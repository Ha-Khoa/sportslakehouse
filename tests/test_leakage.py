"""Leakage tests 1 and 2 from the design doc (section 9.9), run on the real Silver/Gold data.

Run `make dbt` first. Marker `data`: they only run with `make test-data`.

Test 1: recompute rolling form in plain Python from strictly earlier matches and compare it
        with the Gold table (a second, independent implementation).
Test 2: add future matches and check that the features of past matches do not move.
"""

import math
from pathlib import Path

import duckdb
import jinja2
import numpy as np
import pandas as pd
import pytest

from sportslakehouse.config import Settings

pytestmark = pytest.mark.data

ROOT = Path(__file__).resolve().parents[1]
FORM_MODEL = ROOT / "dbt_project" / "models" / "gold" / "int_team_form.sql"


@pytest.fixture(scope="module")
def paths():
    s = Settings()
    tm = s.silver_dir / "team_matches.parquet"
    fct = s.gold_dir / "fct_match_features.parquet"
    if not tm.exists() or not fct.exists():
        pytest.skip("Silver/Gold Parquet missing: run `make dbt` first")
    return tm, fct


def _read(path: Path) -> pd.DataFrame:
    con = duckdb.connect()
    try:
        return con.execute("select * from read_parquet(?)", [str(path)]).df()
    finally:
        con.close()


# ------------------------------------------------------------------------------- test 1
def test_ppg_10_matches_independent_python_recomputation(paths):
    tm_path, fct_path = paths
    tm = _read(tm_path)
    fct = _read(fct_path)

    # history per team, sorted the same way as the SQL window: (match_date, match_id)
    history = {
        team: g.sort_values(["match_date", "match_id"]).reset_index(drop=True)
        for team, g in tm.groupby("team_id")
    }

    sample = fct.sample(n=400, random_state=42)
    checked = 0
    for row in sample.itertuples(index=False):
        for side, team, col_ppg, col_n in [
            ("home", row.home_team_id, "h_ppg_10", "h_n_prev_10"),
            ("away", row.away_team_id, "a_ppg_10", "a_n_prev_10"),
        ]:
            hist = history[team]
            earlier = hist[hist["match_date"] < row.match_date].tail(10)  # strictly before
            expected_n = len(earlier)
            expected_ppg = earlier["points"].mean() if expected_n else math.nan
            actual_ppg = getattr(row, col_ppg)
            assert getattr(row, col_n) == expected_n, (side, team, row.match_date)
            if expected_n == 0:
                assert pd.isna(actual_ppg), (side, team, row.match_date)
            else:
                assert math.isclose(actual_ppg, expected_ppg, abs_tol=1e-9), (
                    side,
                    team,
                    row.match_date,
                )
            checked += 1
    assert checked == 800


# ------------------------------------------------------------------------------- test 2
def _render_form_sql(table_name: str) -> str:
    """Render the dbt model with jinja2, pointing ref('silver_team_matches') at a plain table."""

    def ref(name: str) -> str:
        assert name == "silver_team_matches", f"unexpected ref {name}"
        return table_name

    return jinja2.Template(FORM_MODEL.read_text(encoding="utf-8")).render(
        ref=ref, config=lambda **kwargs: ""
    )


@pytest.mark.parametrize("cut_date", ["2005-03-01", "2013-12-15", "2022-01-20"])
def test_adding_future_matches_does_not_change_past_features(paths, cut_date):
    tm_path, _ = paths
    con = duckdb.connect()
    try:
        con.execute("create table tm_full as select * from read_parquet(?)", [str(tm_path)])
        con.execute(
            f"create table tm_cut as select * from tm_full where match_date < DATE '{cut_date}'"
        )

        full = con.execute(_render_form_sql("tm_full")).df()
        cut = con.execute(_render_form_sql("tm_cut")).df()
    finally:
        con.close()

    past = full[full["match_date"] < pd.Timestamp(cut_date)]
    assert len(cut) > 1000 and len(cut) == len(past) < len(full)  # the cut really removed future

    keys = ["match_id", "team_id"]
    pd.testing.assert_frame_equal(
        past.sort_values(keys).reset_index(drop=True),
        cut.sort_values(keys).reset_index(drop=True),
        check_dtype=False,
    )


def test_features_react_to_the_past_not_the_future_sanity(paths):
    """Guard against a vacuous test 2: the cut data must differ from full data somewhere."""
    tm_path, _ = paths
    con = duckdb.connect()
    try:
        con.execute("create table tm_full as select * from read_parquet(?)", [str(tm_path)])
        con.execute(
            "create table tm_cut as select * from tm_full where match_date < DATE '2013-12-15'"
        )
        full = con.execute(_render_form_sql("tm_full")).df()
        cut = con.execute(_render_form_sql("tm_cut")).df()
    finally:
        con.close()
    assert len(full) > len(cut)
    assert not np.isnan(full["ppg_10"]).all()
