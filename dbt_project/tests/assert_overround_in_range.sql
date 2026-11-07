{{ config(severity='warn') }}
-- Sum of implied probabilities (1/odds) is the bookmaker margin: expected between 1.0 and 1.2.
select
    match_id, bookmaker, is_closing,
    1 / odds_home + 1 / odds_draw + 1 / odds_away as implied_sum
from {{ ref('silver_match_odds') }}
where 1 / odds_home + 1 / odds_draw + 1 / odds_away not between 1.0 and 1.2
