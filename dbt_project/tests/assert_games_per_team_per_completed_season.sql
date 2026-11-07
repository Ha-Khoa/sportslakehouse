-- Every team plays exactly 34 matches in a completed season.
with games as (
    select season, home_team_name as team_name from {{ ref('stg_fd_matches') }}
    union all
    select season, away_team_name from {{ ref('stg_fd_matches') }}
),
per_team as (
    select season, team_name, count(*) as n_games
    from games
    group by season, team_name
),
latest as (
    select max(season) as latest_season from per_team
)
select p.season, p.team_name, p.n_games
from per_team p
cross join latest l
where p.season < l.latest_season
  and p.n_games <> {{ var('games_per_team_per_completed_season') }}
