{{ config(
    materialized='external',
    format='parquet',
    location=var('lake_dir') ~ '/silver/teams.parquet',
    alias='teams'
) }}

with span as (

    select
        team_id,
        min(season)            as first_season,
        max(season)            as last_season,
        count(distinct season) as seasons_played
    from {{ ref('silver_team_matches') }}
    group by team_id

),

names as (

    select distinct team_id, team_name
    from {{ ref('team_name_map') }}

)

select
    names.team_id,
    names.team_name,
    span.first_season,
    span.last_season,
    span.seasons_played
from names
inner join span using (team_id)
order by names.team_id
