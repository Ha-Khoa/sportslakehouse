{#
  Rows that failed a row-level rule never disappear silently: they land here with the reason.
  Kept as a plain table (not Parquet): it is normally empty and only read by the quality report.
#}
{{ config(materialized='table', alias='quarantine_matches') }}

select
    season,
    source_row_number,
    match_date,
    home_team_name,
    away_team_name,
    home_goals,
    away_goals,
    result,
    quarantine_reason
from {{ ref('int_matches_checked') }}
where quarantine_reason is not null
