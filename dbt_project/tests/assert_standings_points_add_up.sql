-- For every completed season the final table must contain every point handed out in the matches.
with final_table as (
    select season, sum(points) as table_points, sum(goals_for) as table_goals_for,
           sum(goals_against) as table_goals_against, count(*) as n_teams
    from {{ ref('mart_standings') }}
    where matches_played = {{ var('games_per_team_per_completed_season') }}
    group by season
),
from_matches as (
    select season, sum(points) as match_points
    from {{ ref('silver_team_matches') }}
    group by season
)
select f.season, f.table_points, m.match_points, f.table_goals_for, f.table_goals_against
from final_table f
inner join from_matches m using (season)
where f.table_points <> m.match_points
   or f.table_goals_for <> f.table_goals_against   -- every goal scored is also conceded
