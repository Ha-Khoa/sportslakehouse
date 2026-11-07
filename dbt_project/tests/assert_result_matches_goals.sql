-- result (H/D/A) must agree with the goals. Independent re-check of the quarantine rule.
select match_id, home_goals, away_goals, result
from {{ ref('silver_matches') }}
where result <> case
                    when home_goals > away_goals then 'H'
                    when home_goals < away_goals then 'A'
                    else 'D'
                end
