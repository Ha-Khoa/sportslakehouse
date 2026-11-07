-- goals_for of one side must equal goals_against of the other side of the same match.
select h.match_id
from {{ ref('silver_team_matches') }} h
join {{ ref('silver_team_matches') }} a
  on h.match_id = a.match_id and h.is_home and not a.is_home
where h.goals_for <> a.goals_against or h.goals_against <> a.goals_for
