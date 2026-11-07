-- A team's first-ever Elo value is the start rating: 1500 in the first season of the data,
-- 1400 (promoted_start) for a team that appears later. Anything else means a bug.
with first_rows as (
    select e.team_id, e.elo_pre, m.season,
           row_number() over (partition by e.team_id order by m.match_date, m.match_id) as rn
    from {{ ref('elo_ratings') }} e
    inner join {{ ref('silver_matches') }} m using (match_id)
),
first_season as (
    select min(season) as s from {{ ref('silver_matches') }}
)
select f.team_id, f.elo_pre, f.season
from first_rows f
cross join first_season fs
where f.rn = 1
  and f.elo_pre <> case when f.season = fs.s then 1500.0 else 1400.0 end
