select match_id, count(*) as n_rows
from {{ ref('elo_ratings') }}
group by match_id
having count(*) <> 2
