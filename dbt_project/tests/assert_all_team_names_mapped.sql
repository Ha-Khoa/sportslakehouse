-- A team name in the data that is not in the seed (new club, new spelling) must stop the pipeline.
with names as (
    select home_team_name as team_name from {{ ref('stg_fd_matches') }}
    union
    select away_team_name from {{ ref('stg_fd_matches') }}
),
mapped as (
    select source_name from {{ ref('team_name_map') }} where source = 'football_data'
)
select names.team_name
from names
left join mapped on names.team_name = mapped.source_name
where mapped.source_name is null
