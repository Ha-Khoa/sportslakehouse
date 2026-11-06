"""Download football-data.co.uk CSVs and turn them into Bronze Parquet.

Bronze rules (see design doc, section 5.3 and 7):
  * keep the source as it is: every column is stored as a string, nothing is converted;
  * add audit columns (_season, _league, _source_url, _file_hash, _ingested_at, _row_number);
  * partition by season, overwrite exactly one partition per run (idempotent);
  * tolerate schema drift: seasons do not share the same set of columns.
"""

from __future__ import annotations

import hashlib
import io
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import pandas as pd

from sportslakehouse.config import REQUIRED_COLUMNS, Settings
from sportslakehouse.seasons import fd_code, is_completed, season_label


class SchemaError(ValueError):
    """Raised when a downloaded file lacks a required column or is not a CSV."""


class _Response(Protocol):
    status_code: int
    content: bytes

    def raise_for_status(self) -> None: ...


class _Session(Protocol):
    def get(self, url: str, **kwargs: Any) -> _Response: ...


@dataclass(frozen=True)
class DownloadResult:
    season: str
    url: str
    path: Path
    sha256: str
    from_cache: bool


# --------------------------------------------------------------------- helpers
def build_url(start_year: int, settings: Settings) -> str:
    return f"{settings.base_url}/{fd_code(start_year)}/{settings.league}.csv"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _cache_path(start_year: int, settings: Settings) -> Path:
    return settings.raw_cache_dir / season_label(start_year) / f"{settings.league}.csv"


# -------------------------------------------------------------------- download
def download_season(
    start_year: int,
    settings: Settings,
    *,
    session: _Session | None = None,
    force: bool = False,
    retries: int = 3,
) -> DownloadResult:
    """Download one season, or reuse the cached file.

    Completed seasons are static, so they are downloaded once. The current season is always
    re-downloaded because the source corrects results and adds odds late.
    """
    label = season_label(start_year)
    url = build_url(start_year, settings)
    path = _cache_path(start_year, settings)

    if path.exists() and not force and is_completed(start_year):
        data = path.read_bytes()
        return DownloadResult(label, url, path, sha256_bytes(data), from_cache=True)

    if session is None:
        import requests

        session = requests.Session()

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(
                url,
                timeout=settings.http_timeout_s,
                headers={"User-Agent": settings.user_agent},
            )
            resp.raise_for_status()
            data = resp.content
            if data.lstrip()[:1] == b"<":
                raise SchemaError(f"{url} returned HTML, not CSV")
            break
        except Exception as exc:  # noqa: BLE001 - we re-raise after the last attempt
            last_error = exc
            if attempt == retries:
                raise
            time.sleep(2**attempt)
    else:  # pragma: no cover
        raise RuntimeError(f"download failed: {last_error}")

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".csv.tmp")
    tmp.write_bytes(data)
    tmp.replace(path)  # atomic: never leave a half-written cache file
    return DownloadResult(label, url, path, sha256_bytes(data), from_cache=False)


# ----------------------------------------------------------------------- clean
def _decode(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise SchemaError("Cannot decode file")  # pragma: no cover (latin-1 never fails)


def clean_raw_csv(raw: bytes) -> pd.DataFrame:
    """Parse a raw CSV into an all-string DataFrame without changing any values.

    Only structural clean-up happens here: strip whitespace, drop unnamed (empty) columns and
    completely empty rows. Real cleaning (types, team names) belongs to Silver.
    """
    text = _decode(raw)
    df = pd.read_csv(
        io.StringIO(text),
        dtype=str,
        keep_default_na=False,
        na_filter=False,
        index_col=False,  # old files have trailing commas; avoid shifting columns
        on_bad_lines="warn",
        skipinitialspace=True,
    )
    df.columns = [str(c).strip() for c in df.columns]
    keep = [c for c in df.columns if c and not c.startswith("Unnamed")]
    df = df[keep]
    df = df.apply(lambda col: col.str.strip())
    df = df[(df != "").any(axis=1)].reset_index(drop=True)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise SchemaError(f"Missing required columns: {missing}")
    return df


def add_audit_columns(
    df: pd.DataFrame,
    *,
    season: str,
    league: str,
    url: str,
    file_hash: str,
    ingested_at: datetime | None = None,
) -> pd.DataFrame:
    out = df.copy()
    ts = (ingested_at or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    out["_season"] = season
    out["_league"] = league
    out["_source_url"] = url
    out["_file_hash"] = file_hash
    out["_ingested_at"] = ts
    out["_row_number"] = range(1, len(out) + 1)
    out["_row_number"] = out["_row_number"].astype(str)  # Bronze stays all-string
    return out


# ----------------------------------------------------------------------- write
def bronze_partition_path(season: str, settings: Settings) -> Path:
    return settings.bronze_dir / f"season={season}" / f"{settings.league}.parquet"


def write_bronze(df: pd.DataFrame, season: str, settings: Settings) -> Path:
    """Overwrite exactly one season partition (idempotent)."""
    path = bronze_partition_path(season, settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".parquet.tmp")
    df.to_parquet(tmp, index=False)  # requires pyarrow
    tmp.replace(path)
    return path


# ------------------------------------------------------------------------- log
def last_logged_hash(season: str, settings: Settings) -> str | None:
    """File hash of the most recent ingestion of this season, if any."""
    log = settings.ingestion_log_path
    if not log.exists():
        return None
    last = None
    for line in log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("season") == season:
            last = rec.get("file_hash")
    return last


def append_ingestion_log(record: dict[str, Any], settings: Settings) -> None:
    settings.bronze_meta_dir.mkdir(parents=True, exist_ok=True)
    with settings.ingestion_log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
