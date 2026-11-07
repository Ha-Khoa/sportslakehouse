-- Decimal odds of 1.0 or less are impossible.
select *
from {{ ref('silver_match_odds') }}
where odds_home <= 1 or odds_draw <= 1 or odds_away <= 1
