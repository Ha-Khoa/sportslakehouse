"""Data tests against the real Bronze layer. Run `make bronze` first (marker: data)."""

import csv
import io

import pandas as pd
import pytest

from sportslakehouse.config import REQUIRED_COLUMNS, Settings
from sportslakehouse.ingestion.inventory import load_bronze_frames
from sportslakehouse.seasons import current_season_start, season_label

pytestmark = pytest.mark.data

# Known gaps in the upstream football-data.co.uk files (verified against the raw CSVs).
# Pinned to exact counts so any further change in these seasons still fails the test.
KNOWN_INCOMPLETE = {"2002-03": 290, "2003-04": 194}


@pytest.fixture(scope="module")
def frames():
    frames = load_bronze_frames(Settings())
    if not frames:
        pytest.skip("Bronze layer is empty: run `make bronze` first")
    return frames


def test_all_completed_seasons_have_306_matches(frames):
    current = season_label(current_season_start())
    bad = {
        s: len(df)
        for s, df in frames.items()
        # if s != current and len(df) != KNOWN_INCOMPLETE.get(s, 306)
        if s != current and len(df) != 306
    }
    assert not bad, f"Seasons with unexpected match counts: {bad}"


def test_required_columns_everywhere(frames):
    for season, df in frames.items():
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        assert not missing, f"{season}: missing {missing}"


def test_result_matches_goals(frames):
    for season, df in frames.items():
        hg = pd.to_numeric(df["FTHG"], errors="coerce")
        ag = pd.to_numeric(df["FTAG"], errors="coerce")
        expected = (hg > ag).map({True: "H", False: "A"}).where(hg != ag, "D")
        mismatch = (expected != df["FTR"]).sum()
        assert mismatch == 0, f"{season}: {mismatch} rows where FTR disagrees with goals"


def test_no_duplicate_matches(frames):
    for season, df in frames.items():
        dup = df.duplicated(subset=["Date", "HomeTeam", "AwayTeam"]).sum()
        assert dup == 0, f"{season}: {dup} duplicated matches"


def test_audit_columns_present(frames):
    for season, df in frames.items():
        assert (df["_season"] == season).all()
        assert df["_file_hash"].nunique() == 1


def test_bronze_rows_equal_raw_rows(frames):
    s = Settings()
    for season, df in frames.items():
        path = s.raw_cache_dir / season / f"{s.league}.csv"
        if not path.exists():
            continue
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
        rows = list(csv.reader(io.StringIO(text)))[1:]
        n_raw = sum(1 for r in rows if any(v.strip() for v in r))
        assert len(df) == n_raw, f"{season}: bronze {len(df)} vs raw {n_raw}"
