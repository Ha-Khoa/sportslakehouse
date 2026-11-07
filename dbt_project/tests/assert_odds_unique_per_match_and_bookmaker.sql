select match_id, bookmaker, is_closing, count(*) as n
from {{ ref('silver_match_odds') }}
group by match_id, bookmaker, is_closing
having count(*) > 1
