{#
  League table after every team's k-th match of a season. Grain (season, matches_played, team_id).
  "Round" is approximated by matches_played: a team's k-th match. Postponed matches make
  this differ from the official matchday for a few rows; the FINAL table of a completed season
  (matches_played = 34) is exact.
  Tie-break: points, goal difference, goals scored, then team_id (so the rank is deterministic).
  The real Bundesliga rules can differ for exact ties on all three; see the test of final tables.
#}
{{ config(
    materialized='external',
    format='parquet',
    location=var('lake_dir') ~ '/gold/mart_standings.parquet'
) }}

with running as (

    select
        season,
        team_id,
        match_date,
        count(*)                                   over w as matches_played,
        sum(points)                                over w as points,
        sum(case when points = 3 then 1 else 0 end) over w as wins,
        sum(case when points = 1 then 1 else 0 end) over w as draws,
        sum(case when points = 0 then 1 else 0 end) over w as losses,
        sum(goals_for)                             over w as goals_for,
        sum(goals_against)                         over w as goals_against
    from {{ ref('silver_team_matches') }}
    window w as (partition by season, team_id
                 order by match_date, match_id
                 rows between unbounded preceding and current row)

)

select
    season,
    matches_played,
    team_id,
    match_date,
    points,
    wins,
    draws,
    losses,
    goals_for,
    goals_against,
    goals_for - goals_against as goal_difference,
    row_number() over (
        partition by season, matches_played
        order by points desc, goals_for - goals_against desc, goals_for desc, team_id
    ) as rank
from running
order by season, matches_played, rank
