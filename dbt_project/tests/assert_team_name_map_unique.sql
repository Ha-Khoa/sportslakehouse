-- The pair (source, source_name) must identify exactly one team_id.
select source, source_name, count(*) as n
from {{ ref('team_name_map') }}
group by source, source_name
having count(*) > 1
