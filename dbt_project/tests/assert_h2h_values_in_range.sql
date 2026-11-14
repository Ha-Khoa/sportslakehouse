select match_id, team_id, h2h_n, h2h_ppg_last_3
from {{ ref('int_h2h') }}
where h2h_n not between 0 and 3
   or h2h_ppg_last_3 not between 0 and 3
   or (h2h_n = 0 and h2h_ppg_last_3 is not null)
