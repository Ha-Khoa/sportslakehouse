"""Turn dbt's run_results.json into a quality history and a readable report.

`make quality-report` after `make dbt`:
  * appends the test results of the last dbt run to data/lake/gold/_meta/dbt_test_history.jsonl
    (once per dbt invocation, so running it twice does not duplicate anything);
  * writes data/lake/gold/mart_data_quality.parquet (the whole history, for the dashboard);
  * writes docs/quality_report.md (summary of the last run + data coverage tables).

The parsing functions are pure (dicts in, dicts out), so tests/test_dbt_results.py covers them
without dbt.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import duckdb

from sportslakehouse.config import Settings

ROOT = Path(__file__).resolve().parents[3]
RUN_RESULTS = ROOT / "dbt_project" / "target" / "run_results.json"
REPORT = ROOT / "docs" / "quality_report.md"


def parse_run_results(data: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per dbt TEST in the run (models, seeds and hooks are skipped)."""
    meta = data.get("metadata", {})
    rows = []
    for res in data.get("results", []):
        unique_id = res.get("unique_id", "")
        if not unique_id.startswith("test."):
            continue
        rows.append(
            {
                "invocation_id": meta.get("invocation_id"),
                "run_at": meta.get("generated_at"),
                "test_name": unique_id.split(".")[2],
                "status": res.get("status"),  # pass | warn | fail | error | skipped
                "failures": res.get("failures") or 0,
                "seconds": round(float(res.get("execution_time") or 0.0), 4),
            }
        )
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(r["status"] for r in rows)
    return {"total": len(rows), **dict(counts)}


def append_history(rows: list[dict[str, Any]], path: Path) -> bool:
    """Append rows unless this invocation is already in the file. Returns True if appended."""
    if not rows:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    invocation = rows[0]["invocation_id"]
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() and json.loads(line).get("invocation_id") == invocation:
                return False
    with path.open("a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    return True


def _coverage_tables(settings: Settings) -> str:
    """Per-season coverage of shots and odds, computed from Silver (design doc, section 8)."""
    matches = settings.silver_dir / "matches.parquet"
    odds = settings.silver_dir / "match_odds.parquet"
    if not matches.exists() or not odds.exists():
        return "_Silver Parquet not found: run `make dbt` first._\n"
    con = duckdb.connect()
    try:
        df = con.execute(
            """
            with closing as (
                select distinct match_id from read_parquet(?) where is_closing
            )
            select
                m.season,
                count(*) as matches,
                round(100.0 * avg(case when m.home_shots is not null then 1 else 0 end), 1)
                    as pct_with_shots,
                round(
                    100.0 * avg(case when m.home_shots_on_target is not null then 1 else 0 end), 1
                ) as pct_with_shots_on_target,
                round(100.0 * avg(case when c.match_id is not null then 1 else 0 end), 1)
                    as pct_with_closing_odds
            from read_parquet(?) m
            left join closing c using (match_id)
            group by m.season
            order by m.season
            """,
            [str(odds), str(matches)],
        ).df()
    finally:
        con.close()
    lines = [
        "| season | matches | % shots | % shots on target | % closing odds |",
        "|---|---|---|---|---|",
    ]
    for r in df.itertuples(index=False):
        lines.append(
            f"| {r.season} | {r.matches} | {r.pct_with_shots} | "
            f"{r.pct_with_shots_on_target} | {r.pct_with_closing_odds} |"
        )
    return "\n".join(lines) + "\n"


def _quarantine_summary(settings: Settings) -> str:
    db = settings.data_dir / "warehouse.duckdb"
    if not db.exists():
        return "_warehouse.duckdb not found._\n"
    con = duckdb.connect(str(db), read_only=True)
    try:
        rows = con.execute(
            "select quarantine_reason, count(*) from silver.quarantine_matches group by 1"
        ).fetchall()
    except duckdb.Error as exc:
        return f"_Could not read silver.quarantine_matches: {exc}_\n"
    finally:
        con.close()
    if not rows:
        return "No rows in quarantine.\n"
    return "\n".join(f"- {reason}: {n}" for reason, n in rows) + "\n"


def render_report(rows: list[dict[str, Any]], settings: Settings) -> str:
    s = summarize(rows)
    bad = [r for r in rows if r["status"] != "pass"]
    out = [
        "# Data quality report",
        "",
        f"Generated from the last dbt run ({rows[0]['run_at'] if rows else 'n/a'}).",
        "",
        "## dbt tests in the last run",
        "",
        "| total | " + " | ".join(k for k in s if k != "total") + " |",
        "|---|" + "---|" * (len(s) - 1),
        "| " + " | ".join(str(v) for v in s.values()) + " |",
        "",
    ]
    if bad:
        out += ["Tests that did not pass:", ""]
        out += [f"- `{r['test_name']}`: {r['status']} ({r['failures']} rows)" for r in bad]
    else:
        out += ["All tests passed."]
    out += [
        "",
        "## Quarantine (rows rejected by a row-level rule)",
        "",
        _quarantine_summary(settings),
        "",
        "## Coverage of shots and closing odds per season",
        "",
        _coverage_tables(settings),
    ]
    return "\n".join(out)


def main() -> int:
    if not RUN_RESULTS.exists():
        print(f"{RUN_RESULTS} not found: run `make dbt` first", file=sys.stderr)
        return 1
    settings = Settings()
    rows = parse_run_results(json.loads(RUN_RESULTS.read_text(encoding="utf-8")))
    history = settings.gold_dir / "_meta" / "dbt_test_history.jsonl"
    appended = append_history(rows, history)

    con = duckdb.connect()
    try:
        con.execute(
            "copy (select * from read_json_auto(?)) to ? (format parquet)",
            [str(history), str(settings.gold_dir / "mart_data_quality.parquet")],
        )
    finally:
        con.close()

    REPORT.write_text(render_report(rows, settings), encoding="utf-8")
    print(f"tests in last run: {summarize(rows)} | history appended: {appended}")
    print(f"wrote {REPORT.relative_to(ROOT)} and mart_data_quality.parquet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
