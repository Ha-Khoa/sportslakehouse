-- A match hands out 3 points (win) or 2 points (draw) in total.
select match_id, sum(points) as total_points
from {{ ref('silver_team_matches') }}
group by match_id
having sum(points) not in (2, 3)
