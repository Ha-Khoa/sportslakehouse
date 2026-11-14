"""Pure-Python tests for the dbt result parser (no dbt, no DuckDB)."""

import json

from sportslakehouse.quality.dbt_results import append_history, parse_run_results, summarize

FAKE = {
    "metadata": {"invocation_id": "abc", "generated_at": "2026-11-07T06:00:00Z"},
    "results": [
        {"unique_id": "model.sportslakehouse.silver_matches", "status": "success"},
        {
            "unique_id": "test.sportslakehouse.not_null_silver_matches_match_id.f1",
            "status": "pass",
            "failures": 0,
            "execution_time": 0.012,
        },
        {
            "unique_id": "test.sportslakehouse.assert_overround_in_range",
            "status": "warn",
            "failures": 3,
            "execution_time": 0.5,
        },
    ],
}


def test_only_tests_are_kept_and_names_are_extracted():
    rows = parse_run_results(FAKE)
    assert [r["test_name"] for r in rows] == [
        "not_null_silver_matches_match_id",
        "assert_overround_in_range",
    ]
    assert rows[1]["failures"] == 3


def test_summary_counts_by_status():
    assert summarize(parse_run_results(FAKE)) == {"total": 2, "pass": 1, "warn": 1}


def test_history_is_written_once_per_invocation(tmp_path):
    path = tmp_path / "meta" / "history.jsonl"
    rows = parse_run_results(FAKE)
    assert append_history(rows, path) is True
    assert append_history(rows, path) is False  # same invocation: no duplicates
    assert len(path.read_text().splitlines()) == 2
    assert json.loads(path.read_text().splitlines()[0])["invocation_id"] == "abc"
