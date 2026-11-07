-- Every season except the newest one must have exactly 306 matches (18 teams x 34 / 2).
-- Counted on staging, before any row can be quarantined, so a lost row is always visible.
-- This is the test that would have caught the 290/194-match bug of week 1.
with per_season as (
    select season, count(*) as n_matches
    from {{ ref('stg_fd_matches') }}
    group by season
),
latest as (
    select max(season) as latest_season from per_season
)
select p.season, p.n_matches
from per_season p
cross join latest l
where p.season < l.latest_season
  and p.n_matches <> {{ var('matches_per_completed_season') }}
