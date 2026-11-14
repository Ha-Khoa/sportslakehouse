-- In every (season, matches_played) group the ranks must be exactly 1..n, each used once.
select season, matches_played, count(*) as n_teams, count(distinct rank) as n_ranks, max(rank) as max_rank
from {{ ref('mart_standings') }}
group by season, matches_played
having count(*) <> count(distinct rank) or max(rank) <> count(*)
