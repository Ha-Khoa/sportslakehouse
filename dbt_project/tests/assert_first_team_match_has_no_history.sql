-- The very first match of every team must have an empty window (n_prev_10 = 0, ppg_10 NULL).
with first_match as (
    select team_id, min(match_date) as first_date
    from {{ ref('silver_team_matches') }}
    group by team_id
)
select f.match_id, f.team_id, f.n_prev_10, f.ppg_10
from {{ ref('int_team_form') }} f
inner join first_match m on m.team_id = f.team_id and m.first_date = f.match_date
where f.n_prev_10 <> 0 or f.ppg_10 is not null
