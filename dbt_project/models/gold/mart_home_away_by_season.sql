{#
  Home advantage per season: result shares and average goals. Shows the COVID seasons
  (2019-20 after the restart, 2020-21) without spectators.
#}
{{ config(
    materialized='external',
    format='parquet',
    location=var('lake_dir') ~ '/gold/mart_home_away_by_season.parquet'
) }}

select
    season,
    count(*)                                          as n_matches,
    avg(case when result = 'H' then 1.0 else 0.0 end) as home_win_rate,
    avg(case when result = 'D' then 1.0 else 0.0 end) as draw_rate,
    avg(case when result = 'A' then 1.0 else 0.0 end) as away_win_rate,
    avg(home_goals)                                   as avg_home_goals,
    avg(away_goals)                                   as avg_away_goals
from {{ ref('silver_matches') }}
group by season
order by season
