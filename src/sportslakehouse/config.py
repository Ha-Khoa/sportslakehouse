"""Central configuration. Values come from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_COLUMNS = ("Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR")


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(os.environ.get("DATA_DIR", "./data")))
    base_url: str = field(
        default_factory=lambda: os.environ.get(
            "FD_BASE_URL", "https://www.football-data.co.uk/mmz4281"
        )
    )
    league: str = field(default_factory=lambda: os.environ.get("FD_LEAGUE", "D1"))
    first_season_start: int = field(
        default_factory=lambda: int(os.environ.get("FIRST_SEASON_START", "2000"))
    )
    http_timeout_s: float = field(
        default_factory=lambda: float(os.environ.get("HTTP_TIMEOUT_S", "30"))
    )
    polite_delay_s: float = field(
        default_factory=lambda: float(os.environ.get("POLITE_DELAY_S", "1.0"))
    )
    user_agent: str = "sportslakehouse/0.1 (educational project)"

    # ---- derived paths -------------------------------------------------
    @property
    def raw_cache_dir(self) -> Path:
        return self.data_dir / "raw_cache" / "football_data"

    @property
    def bronze_dir(self) -> Path:
        return self.data_dir / "lake" / "bronze" / "football_data"

    @property
    def bronze_meta_dir(self) -> Path:
        return self.data_dir / "lake" / "bronze" / "_meta"

    @property
    def ingestion_log_path(self) -> Path:
        return self.bronze_meta_dir / "ingestion_log.jsonl"

    @property
    def column_inventory_path(self) -> Path:
        return self.bronze_meta_dir / "column_inventory.parquet"
