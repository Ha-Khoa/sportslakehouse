-- Each match has exactly two rows: one home, one away.
select match_id, count(*) as n_rows, sum(case when is_home then 1 else 0 end) as n_home
from {{ ref('silver_team_matches') }}
group by match_id
having count(*) <> 2 or sum(case when is_home then 1 else 0 end) <> 1
