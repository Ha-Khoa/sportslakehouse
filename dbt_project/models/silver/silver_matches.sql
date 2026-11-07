{{ config(
    materialized='external',
    format='parquet',
    location=var('lake_dir') ~ '/silver/matches.parquet',
    alias='matches'
) }}

select
    match_id,
    season,
    match_date,
    home_team_id,
    away_team_id,
    home_goals,
    away_goals,
    result,
    ht_home_goals,
    ht_away_goals,
    home_shots,
    away_shots,
    home_shots_on_target,
    away_shots_on_target
from {{ ref('int_matches_checked') }}
where quarantine_reason is null
order by match_date, match_id
