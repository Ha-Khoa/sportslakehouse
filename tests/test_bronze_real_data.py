"""Data tests against the real Bronze layer. Run `make bronze` first (marker: data)."""

import pandas as pd
import pytest

from sportslakehouse.config import REQUIRED_COLUMNS, Settings
from sportslakehouse.ingestion.inventory import load_bronze_frames
from sportslakehouse.seasons import current_season_start, season_label

pytestmark = pytest.mark.data


@pytest.fixture(scope="module")
def frames():
    frames = load_bronze_frames(Settings())
    if not frames:
        pytest.skip("Bronze layer is empty: run `make bronze` first")
    return frames


def test_all_completed_seasons_have_306_matches(frames):
    current = season_label(current_season_start())
    bad = {s: len(df) for s, df in frames.items() if s != current and len(df) != 306}
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
