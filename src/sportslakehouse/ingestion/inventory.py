"""Column inventory: which column appears in which season, and how often it is empty.

Odds and match-statistics columns differ between seasons. Instead of assuming a schema, we
record what really exists. Silver models read this to choose reference columns, and a test
warns when a required column disappears.
"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from sportslakehouse.config import Settings

AUDIT_PREFIX = "_"


def inventory_from_frames(frames: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Build the inventory from {season_label: all-string DataFrame}."""
    rows = []
    for season, df in sorted(frames.items()):
        n = len(df)
        for col in df.columns:
            if col.startswith(AUDIT_PREFIX):
                continue
            empty = int((df[col].astype(str).str.strip() == "").sum())
            rows.append(
                {
                    "season": season,
                    "column": col,
                    "n_rows": n,
                    "empty_share": round(empty / n, 4) if n else 1.0,
                }
            )
    return pd.DataFrame(rows, columns=["season", "column", "n_rows", "empty_share"])


def columns_by_season(inv: pd.DataFrame, min_filled: float = 0.5) -> pd.DataFrame:
    """Wide table: rows = column, cols = season, value = 1 if present and mostly filled."""
    if inv.empty:
        return pd.DataFrame()
    inv = inv.assign(ok=(inv["empty_share"] <= 1 - min_filled).astype(int))
    return inv.pivot_table(index="column", columns="season", values="ok", fill_value=0)


def first_season_with(inv: pd.DataFrame, column: str, min_filled: float = 0.5) -> str | None:
    """First season in which `column` exists and is at least `min_filled` filled."""
    sub = inv[(inv["column"] == column) & (inv["empty_share"] <= 1 - min_filled)]
    return None if sub.empty else str(sub["season"].min())


def load_bronze_frames(settings: Settings) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for part in sorted(settings.bronze_dir.glob("season=*")):
        file = part / f"{settings.league}.parquet"
        if file.exists():
            frames[part.name.removeprefix("season=")] = pd.read_parquet(file)
    return frames


def write_inventory(settings: Settings) -> pd.DataFrame:
    inv = inventory_from_frames(load_bronze_frames(settings))
    settings.bronze_meta_dir.mkdir(parents=True, exist_ok=True)
    inv.to_parquet(settings.column_inventory_path, index=False)
    return inv
