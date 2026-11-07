-- No team can play the same opponent at home twice on one day.
select match_date, home_team_id, away_team_id, count(*) as n
from {{ ref('silver_matches') }}
group by match_date, home_team_id, away_team_id
having count(*) > 1
