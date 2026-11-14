{#
  Head-to-head history BEFORE each match, from the point of view of `team_id`:
  the points that team took in its previous (up to) 3 meetings with this opponent, home or away.
  Grain (match_id, team_id), same as int_team_form.

  Leakage rule: the window ends at 1 PRECEDING. Like int_team_form it may only use `ref` and
  `config`, because tests/test_leakage.py renders it with jinja2 and runs it on truncated data.
#}
{{ config(materialized='view', schema='staging') }}

select
    match_id,
    team_id,
    count(*)    over w3 as h2h_n,
    avg(points) over w3 as h2h_ppg_last_3
from {{ ref('silver_team_matches') }}
window
    w3 as (partition by team_id, opp_id
           order by match_date, match_id
           rows between 3 preceding and 1 preceding)
