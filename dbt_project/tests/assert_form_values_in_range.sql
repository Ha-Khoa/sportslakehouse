-- Points per game must be between 0 and 3; goal/shot averages cannot be negative.
select match_id, team_id, ppg_10, ppg_5, win_rate_10
from {{ ref('int_team_form') }}
where ppg_10 not between 0 and 3
   or ppg_5 not between 0 and 3
   or win_rate_10 not between 0 and 1
   or gf_10 < 0 or ga_10 < 0
   or rest_days < 1
