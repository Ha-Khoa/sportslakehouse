-- last_5 contains only W/D/L and has min(5, matches played so far) letters.
select team_id, match_date, last_5, n_matches_in_window
from {{ ref('mart_team_form') }}
where last_5 = ''
   or regexp_matches(last_5, '[^WDL]')
   or length(last_5) <> least(5, n_matches_in_window)
