"""The team seed is plain CSV, so it can be tested without dbt or DuckDB."""

import csv
import re
from pathlib import Path

SEED = Path(__file__).resolve().parents[1] / "dbt_project" / "seeds" / "team_name_map.csv"


def _rows() -> list[dict[str, str]]:
    with SEED.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_seed_has_expected_columns():
    assert list(_rows()[0].keys()) == ["source", "source_name", "team_id", "team_name"]


def test_source_name_is_unique_per_source():
    keys = [(r["source"], r["source_name"]) for r in _rows()]
    assert len(keys) == len(set(keys))


def test_no_empty_cells():
    assert all(all(v.strip() for v in r.values()) for r in _rows())


def test_team_id_is_a_lowercase_ascii_slug():
    # ids end up in match_id hashes, S3 paths and API URLs: keep them boring and stable
    slug = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
    bad = [r["team_id"] for r in _rows() if not slug.fullmatch(r["team_id"])]
    assert not bad, bad


def test_team_id_maps_to_one_canonical_name():
    names: dict[str, set[str]] = {}
    for r in _rows():
        names.setdefault(r["team_id"], set()).add(r["team_name"])
    assert all(len(v) == 1 for v in names.values())
