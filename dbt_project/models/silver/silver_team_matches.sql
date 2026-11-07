{#
  The central Silver table: each match becomes TWO rows, one per team's point of view.
  Rolling "last 10 matches" windows then partition by team_id only, home or away does not matter.
#}
{{ config(
    materialized='external',
    format='parquet',
    location=var('lake_dir') ~ '/silver/team_matches.parquet',
    alias='team_matches'
) }}

with m as (

    select * from {{ ref('silver_matches') }}

),

home_side as (

    select
        match_id,
        home_team_id           as team_id,
        away_team_id           as opp_id,
        match_date,
        season,
        true                   as is_home,
        home_goals             as goals_for,
        away_goals             as goals_against,
        case result when 'H' then 3 when 'D' then 1 else 0 end as points,
        home_shots             as shots_for,
        away_shots             as shots_against,
        home_shots_on_target   as sot_for,
        away_shots_on_target   as sot_against
    from m

),

away_side as (

    select
        match_id,
        away_team_id           as team_id,
        home_team_id           as opp_id,
        match_date,
        season,
        false                  as is_home,
        away_goals             as goals_for,
        home_goals             as goals_against,
        case result when 'A' then 3 when 'D' then 1 else 0 end as points,
        away_shots             as shots_for,
        home_shots             as shots_against,
        away_shots_on_target   as sot_for,
        home_shots_on_target   as sot_against
    from m

)

select * from home_side
union all
select * from away_side
order by match_date, match_id, is_home desc
