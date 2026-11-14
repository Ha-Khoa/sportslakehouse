-- A streak cannot be longer than the number of matches the team played that season.
select s.season, s.team_id, s.streak_length, c.n_played
from {{ ref('mart_unbeaten_streaks') }} s
inner join (
    select season, team_id, count(*) as n_played
    from {{ ref('silver_team_matches') }}
    group by season, team_id
) c using (season, team_id)
where s.streak_length > c.n_played or s.streak_length < 1
