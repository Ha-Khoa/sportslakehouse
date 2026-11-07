-- Every team in the seed must appear in the data (catches a typo in a source_name).
select m.team_id
from (select distinct team_id from {{ ref('team_name_map') }}) m
left join {{ ref('silver_teams') }} t using (team_id)
where t.team_id is null
