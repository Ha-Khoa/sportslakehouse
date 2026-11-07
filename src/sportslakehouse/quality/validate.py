"""Run the Pandera schemas on the real Bronze and Silver data: `make validate`.

Exit code 1 if anything fails, so CI (week 4) can use it as a gate.
"""

from __future__ import annotations

import sys

import duckdb
import pandas as pd
import pandera.pandas as pa

from sportslakehouse.config import Settings
from sportslakehouse.quality.schemas import (
    bronze_matches_schema,
    silver_match_odds_schema,
    silver_matches_schema,
)


def read_parquet(pattern: str) -> pd.DataFrame:
    """Read one file or a glob of Parquet files into pandas through DuckDB."""
    con = duckdb.connect()
    try:
        return con.execute(
            "select * from read_parquet(?, union_by_name = true, hive_partitioning = false)",
            [pattern],
        ).df()
    finally:
        con.close()


def check(name: str, df: pd.DataFrame, schema: pa.DataFrameSchema) -> bool:
    try:
        schema.validate(df, lazy=True)  # lazy: collect ALL failures, not just the first
    except pa.errors.SchemaErrors as err:
        print(f"FAIL  {name}: {len(df)} rows, {len(err.failure_cases)} failing cells")
        print(err.failure_cases.head(20).to_string())
        return False
    print(f"ok    {name}: {len(df)} rows")
    return True


def main() -> int:
    s = Settings()
    results = [
        check("bronze.fd_matches_raw", read_parquet(s.bronze_glob), bronze_matches_schema),
        check(
            "silver.matches",
            read_parquet(str(s.silver_dir / "matches.parquet")),
            silver_matches_schema,
        ),
        check(
            "silver.match_odds",
            read_parquet(str(s.silver_dir / "match_odds.parquet")),
            silver_match_odds_schema,
        ),
    ]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
