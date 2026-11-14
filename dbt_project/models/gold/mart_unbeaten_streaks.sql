{#
  Longest unbeaten run (wins and draws) of every team in every season: the classic
  "gaps and islands" problem. Idea: a running count of losses is constant inside a streak
  and goes up by one at every loss, so (team, season, loss_count) names each streak.
#}
{{ config(
    materialized='external',
    format='parquet',
    location=var('lake_dir') ~ '/gold/mart_unbeaten_streaks.parquet'
) }}

with flagged as (

    select
        season,
        team_id,
        match_date,
        points,
        sum(case when points = 0 then 1 else 0 end) over (
            partition by season, team_id
            order by match_date, match_id
            rows between unbounded preceding and current row
        ) as losses_so_far
    from {{ ref('silver_team_matches') }}

),

streaks as (

    select
        season,
        team_id,
        losses_so_far,
        count(*)        as streak_length,
        min(match_date) as streak_start,
        max(match_date) as streak_end
    from flagged
    where points > 0                 -- only wins and draws belong to a streak
    group by season, team_id, losses_so_far

),

ranked as (

    select
        *,
        row_number() over (
            partition by season, team_id
            order by streak_length desc, streak_start
        ) as rn
    from streaks

)

select season, team_id, streak_length, streak_start, streak_end
from ranked
where rn = 1
order by streak_length desc, season, team_id
