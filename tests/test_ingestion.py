import json
from pathlib import Path

import pandas as pd
import pytest

from sportslakehouse.config import Settings
from sportslakehouse.ingestion import football_data as fd
from sportslakehouse.ingestion.inventory import (
    first_season_with,
    inventory_from_frames,
)

# Old-style file: latin-1, trailing commas (-> unnamed column), a blank row, padded cells.
RAW_OLD = (
    "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,\n"
    "D1,25/08/00, Bayern Munich ,Hamburg,4,1,H,\n"
    ",,,,,,,\n"
    "D1,26/08/00,FC Köln,Dortmund,0,0,D,\n"
).encode("latin-1")

RAW_NEW = (
    "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,HS,AS,B365H,B365D,B365A\n"
    "D1,23/08/2024,Leverkusen,M'gladbach,3,2,H,15,9,1.3,5.5,9.0\n"
    "D1,24/08/2024,Dortmund,Heidenheim,2,1,H,12,6,,,\n"
).encode()


def make_settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path)


class FakeResponse:
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, content: bytes):
        self.content = content
        self.calls = 0

    def get(self, url, **kwargs):
        self.calls += 1
        return FakeResponse(self.content)


def test_build_url_and_hash():
    s = Settings()
    assert fd.build_url(2024, s).endswith("/2425/D1.csv")
    assert fd.sha256_bytes(b"abc") == fd.sha256_bytes(b"abc")
    assert fd.sha256_bytes(b"abc") != fd.sha256_bytes(b"abd")


def test_clean_old_file_is_all_strings_and_structural_only():
    df = fd.clean_raw_csv(RAW_OLD)
    assert len(df) == 2  # blank row dropped
    assert not any(c.startswith("Unnamed") for c in df.columns)
    assert set(df.dtypes.astype(str)) == {"str"} or set(df.dtypes.astype(str)) == {"object"}
    assert df.loc[0, "HomeTeam"] == "Bayern Munich"  # whitespace stripped
    assert df.loc[1, "HomeTeam"] == "FC Köln"  # latin-1 decoded
    assert df.loc[0, "FTHG"] == "4"  # still a string: no type conversion in Bronze


def test_clean_keeps_empty_cells_as_empty_strings():
    df = fd.clean_raw_csv(RAW_NEW)
    assert df.loc[1, "B365H"] == ""


def test_missing_required_column_raises():
    bad = b"Date,HomeTeam,AwayTeam\n01/01/20,A,B\n"
    with pytest.raises(fd.SchemaError):
        fd.clean_raw_csv(bad)


def test_audit_columns():
    df = fd.clean_raw_csv(RAW_NEW)
    out = fd.add_audit_columns(df, season="2024-25", league="D1", url="u", file_hash="h")
    for col in ["_season", "_league", "_source_url", "_file_hash", "_ingested_at", "_row_number"]:
        assert col in out.columns
    assert list(out["_row_number"]) == ["1", "2"]
    assert (out["_season"] == "2024-25").all()
    assert "_season" not in df.columns  # input not mutated


def test_download_uses_cache_for_completed_season(tmp_path):
    settings = make_settings(tmp_path)
    session = FakeSession(RAW_NEW)
    first = fd.download_season(2020, settings, session=session)
    second = fd.download_season(2020, settings, session=session)
    assert not first.from_cache and second.from_cache
    assert session.calls == 1
    assert first.sha256 == second.sha256


def test_download_rejects_html(tmp_path):
    settings = make_settings(tmp_path)
    session = FakeSession(b"<html>blocked</html>")
    with pytest.raises(fd.SchemaError):
        fd.download_season(2020, settings, session=session, retries=1)


def test_ingestion_log_roundtrip(tmp_path):
    settings = make_settings(tmp_path)
    assert fd.last_logged_hash("2024-25", settings) is None
    fd.append_ingestion_log({"season": "2024-25", "file_hash": "aaa"}, settings)
    fd.append_ingestion_log({"season": "2023-24", "file_hash": "bbb"}, settings)
    fd.append_ingestion_log({"season": "2024-25", "file_hash": "ccc"}, settings)
    assert fd.last_logged_hash("2024-25", settings) == "ccc"
    lines = settings.ingestion_log_path.read_text().splitlines()
    assert len(lines) == 3 and json.loads(lines[0])["season"] == "2024-25"


def test_inventory_detects_schema_drift():
    old = fd.clean_raw_csv(RAW_OLD)
    new = fd.clean_raw_csv(RAW_NEW)
    inv = inventory_from_frames({"2000-01": old, "2024-25": new})
    assert "HS" not in set(inv[inv["season"] == "2000-01"]["column"])
    assert first_season_with(inv, "HS") == "2024-25"
    # B365H exists in 2024-25 but one of two rows is empty (50% filled) -> still counted
    assert first_season_with(inv, "B365H", min_filled=0.5) == "2024-25"
    assert first_season_with(inv, "B365H", min_filled=0.9) is None
    assert first_season_with(inv, "NOPE") is None
