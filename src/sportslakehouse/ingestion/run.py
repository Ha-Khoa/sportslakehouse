"""CLI: download football-data.co.uk seasons and write the Bronze layer.

Examples
  python -m sportslakehouse.ingestion.run                  # all seasons
  python -m sportslakehouse.ingestion.run --seasons 2024-25,2025-26
  python -m sportslakehouse.ingestion.run --force          # ignore the cache
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone

from sportslakehouse.config import Settings
from sportslakehouse.ingestion.football_data import (
    add_audit_columns,
    append_ingestion_log,
    bronze_partition_path,
    clean_raw_csv,
    download_season,
    last_logged_hash,
    write_bronze,
)
from sportslakehouse.ingestion.inventory import write_inventory
from sportslakehouse.seasons import parse_season, season_label, season_range


def ingest_season(start_year: int, settings: Settings, *, force: bool = False) -> dict:
    label = season_label(start_year)
    dl = download_season(start_year, settings, force=force)
    previous_hash = last_logged_hash(label, settings)
    partition_exists = bronze_partition_path(label, settings).exists()

    if dl.sha256 == previous_hash and partition_exists:
        status = "unchanged"
        rows_read = rows_written = 0
    else:
        df = clean_raw_csv(dl.path.read_bytes())
        rows_read = len(df)
        df = add_audit_columns(
            df,
            season=label,
            league=settings.league,
            url=dl.url,
            file_hash=dl.sha256,
            ingested_at=datetime.now(timezone.utc),
        )
        write_bronze(df, label, settings)
        rows_written = len(df)
        status = "new" if previous_hash is None else "updated"

    record = {
        "season": label,
        "status": status,
        "file_hash": dl.sha256,
        "from_cache": dl.from_cache,
        "rows_read": rows_read,
        "rows_written": rows_written,
        "source_url": dl.url,
        "logged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    append_ingestion_log(record, settings)
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--seasons", default="all", help="'all' or comma list, e.g. 2023-24,2024-25")
    parser.add_argument("--force", action="store_true", help="ignore cached CSV files")
    args = parser.parse_args(argv)

    settings = Settings()
    if args.seasons == "all":
        seasons = season_range(settings.first_season_start)
    else:
        seasons = [parse_season(s) for s in args.seasons.split(",")]

    failures = 0
    print(f"{'season':<9} {'status':<10} {'rows':>6}  cache")
    for i, start in enumerate(seasons):
        try:
            rec = ingest_season(start, settings, force=args.force)
            print(
                f"{rec['season']:<9} {rec['status']:<10} {rec['rows_written']:>6}  "
                f"{'hit' if rec['from_cache'] else 'download'}"
            )
            if not rec["from_cache"] and i < len(seasons) - 1:
                time.sleep(settings.polite_delay_s)  # be polite to the free data provider
        except Exception as exc:  # noqa: BLE001 - report and continue with the next season
            failures += 1
            print(f"{season_label(start):<9} FAILED     {type(exc).__name__}: {exc}", file=sys.stderr)

    inv = write_inventory(settings)
    print(f"\ncolumn inventory: {inv['season'].nunique()} seasons, {inv['column'].nunique()} columns")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
