{#
  Every staging row, plus: canonical team ids, match_id, and `quarantine_reason`.
  quarantine_reason is NULL for a clean row. Rules are checked top to bottom; the first that
  fires is the reason. silver_matches keeps clean rows, silver_quarantine_matches the rest.
  A season runs from July to June (2001-02 really started on 28 July 2001).
#}
{{ config(materialized='view', schema='staging') }}

with stg as (

    select * from {{ ref('stg_fd_matches') }}

),

team_map as (

    select source_name, team_id
    from {{ ref('team_name_map') }}
    where source = 'football_data'

),

joined as (

    select
        stg.*,
        h.team_id as home_team_id,
        a.team_id as away_team_id,
        cast(left(stg.season, 4) as integer) as season_start_year
    from stg
    left join team_map h on stg.home_team_name = h.source_name
    left join team_map a on stg.away_team_name = a.source_name

)

select
    *,
    md5(concat_ws('|', cast(match_date as varchar), home_team_id, away_team_id)) as match_id,
    case
        when match_date is null
            then 'invalid_date'
        when match_date < make_date(season_start_year, 7, 1)
          or match_date > make_date(season_start_year + 1, 6, 30)
            then 'date_outside_season'
        when home_team_id is null or away_team_id is null
            then 'unmapped_team'
        when home_team_id = away_team_id
            then 'same_team'
        when home_goals is null or away_goals is null
            then 'missing_goals'
        when home_goals < 0 or away_goals < 0
            then 'negative_goals'
        when result is null or result not in ('H', 'D', 'A')
            then 'invalid_result'
        when result <> case
                           when home_goals > away_goals then 'H'
                           when home_goals < away_goals then 'A'
                           else 'D'
                       end
            then 'result_mismatch'
    end as quarantine_reason
from joined
