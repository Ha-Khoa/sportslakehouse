"""Unit tests for the pure Elo function. No dbt, no database."""

import math
import random

from sportslakehouse.features.elo import (
    EloParams,
    MatchResult,
    compute_elo,
    expected_home_score,
    goal_diff_multiplier,
)

P = EloParams()


def _m(mid, season, day, home, away, hg, ag):
    return MatchResult(mid, season, day, home, away, hg, ag)


def _pre(rows):
    return {(r.match_id, r.team_id): r.elo_pre for r in rows}


def test_equal_ratings_without_home_advantage_is_a_coin_flip():
    assert math.isclose(expected_home_score(1500, 1500, 0.0), 0.5)


def test_home_advantage_favours_the_home_team():
    assert expected_home_score(1500, 1500, 65.0) > 0.5


def test_goal_difference_multiplier():
    assert goal_diff_multiplier(0) == 1.0
    assert goal_diff_multiplier(-1) == 1.0
    assert goal_diff_multiplier(2) == 1.5
    assert math.isclose(goal_diff_multiplier(3), 14 / 8)
    assert math.isclose(goal_diff_multiplier(-4), 15 / 8)


def test_first_match_of_every_team_in_first_season_starts_at_initial():
    rows = compute_elo([_m("a", "2000-01", "2000-08-12", "X", "Y", 1, 0)], P)
    assert all(r.elo_pre == P.initial for r in rows)


def test_team_that_appears_later_starts_below_average():
    ms = [
        _m("a", "2000-01", "2000-08-12", "X", "Y", 1, 0),
        _m("b", "2001-02", "2001-08-12", "X", "NEW", 1, 0),
    ]
    pre = _pre(compute_elo(ms, P))
    assert pre[("b", "NEW")] == P.promoted_start


def test_winner_gains_and_loser_loses_what_the_winner_gains():
    ms = [
        _m("a", "2000-01", "2000-08-12", "X", "Y", 1, 0),
        _m("b", "2000-01", "2000-08-19", "X", "Y", 1, 0),
    ]
    pre = _pre(compute_elo(ms, P))
    gain = pre[("b", "X")] - P.initial
    assert gain > 0
    assert math.isclose(P.initial - pre[("b", "Y")], gain)  # zero-sum inside a season


def test_new_season_pulls_rating_towards_the_mean():
    ms = [
        _m("a", "2000-01", "2000-08-12", "X", "Y", 1, 0),
        _m("b", "2001-02", "2001-08-12", "X", "Y", 1, 0),
    ]
    pre = _pre(compute_elo(ms, P))
    e = expected_home_score(P.initial, P.initial, P.home_advantage)
    after_a = P.initial + P.k * 1.0 * (1.0 - e)
    expected = P.season_carryover * after_a + (1 - P.season_carryover) * P.initial
    assert math.isclose(pre[("b", "X")], expected)


def test_team_absent_for_two_seasons_is_pulled_twice():
    ms = [
        _m("a", "2000-01", "2000-08-12", "X", "Y", 1, 0),
        _m("b", "2002-03", "2002-08-12", "X", "Z", 1, 0),  # X skipped 2001-02
        _m("c", "2000-01", "2000-09-12", "Z", "Y", 0, 0),
    ]
    pre = _pre(compute_elo(ms, P))
    e = expected_home_score(P.initial, P.initial, P.home_advantage)
    after_a = P.initial + P.k * (1.0 - e)
    carry = P.season_carryover**2
    assert math.isclose(pre[("b", "X")], carry * after_a + (1 - carry) * P.initial)


def test_output_does_not_depend_on_input_order():
    ms = [
        _m(f"m{i}", "2000-01", f"2000-09-{i + 1:02d}", "XY"[i % 2], "XY"[(i + 1) % 2], i % 3, 1)
        for i in range(12)
    ]
    shuffled = ms[:]
    random.Random(1).shuffle(shuffled)
    assert compute_elo(ms, P) == compute_elo(shuffled, P)


# --- leakage test 3 from the design doc (section 9.9) -------------------------------------
def test_pre_match_rating_does_not_depend_on_that_matchs_result():
    base = [
        _m("a", "2000-01", "2000-08-12", "X", "Y", 1, 0),
        _m("b", "2000-01", "2000-08-19", "Y", "Z", 2, 2),
        _m("c", "2000-01", "2000-08-26", "X", "Z", 0, 3),
        _m("d", "2000-01", "2000-09-02", "Z", "Y", 1, 0),
    ]
    flipped = base[:]
    flipped[2] = _m("c", "2000-01", "2000-08-26", "X", "Z", 4, 0)  # change only match c's result
    r1, r2 = _pre(compute_elo(base, P)), _pre(compute_elo(flipped, P))
    for key in [("a", "X"), ("a", "Y"), ("b", "Y"), ("b", "Z"), ("c", "X"), ("c", "Z")]:
        assert r1[key] == r2[key], f"rating before/at match c changed for {key}"
    assert r1[("d", "Z")] != r2[("d", "Z")]  # the change shows up only AFTER match c
