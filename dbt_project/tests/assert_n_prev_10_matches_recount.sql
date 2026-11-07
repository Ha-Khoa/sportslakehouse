-- Leakage test (SQL side): recount the earlier matches of each team with a self-join on
-- strictly earlier dates, a different method than the window function. They must agree.
with tm as (
    select match_id, team_id, match_date from {{ ref('silver_team_matches') }}
),
recount as (
    select a.match_id, a.team_id, count(b.match_id) as n_earlier
    from tm a
    left join tm b on b.team_id = a.team_id and b.match_date < a.match_date
    group by a.match_id, a.team_id
)
select f.match_id, f.team_id, f.n_prev_10, r.n_earlier
from {{ ref('int_team_form') }} f
inner join recount r using (match_id, team_id)
where f.n_prev_10 <> least(r.n_earlier, 10)
