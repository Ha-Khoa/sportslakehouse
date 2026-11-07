{#
  Staging = rename + cast, nothing else. No filtering, no business rules.
  Bronze is all-string, so every cast uses try_cast: a bad value becomes NULL instead of
  crashing the run, and the quarantine rules / not_null tests catch it afterwards.
  Columns that a season does not have arrive as NULL thanks to union_by_name.
  All source columns are double-quoted: "AS" (away shots) is a reserved word in SQL.
#}
with src as (

    select * from {{ source('bronze', 'fd_matches_raw') }}

)

select
    _season                                                     as season,
    try_cast(_row_number as integer)                            as source_row_number,
    _file_hash                                                  as source_file_hash,

    -- two date formats: 8 chars = dd/mm/yy (old files), 10 chars = dd/mm/yyyy
    case
        when length(trim("Date")) = 10 then cast(try_strptime(trim("Date"), '%d/%m/%Y') as date)
        when length(trim("Date")) = 8  then cast(try_strptime(trim("Date"), '%d/%m/%y') as date)
    end                                                         as match_date,

    nullif(trim("HomeTeam"), '')                                as home_team_name,
    nullif(trim("AwayTeam"), '')                                as away_team_name,
    try_cast("FTHG" as integer)                                 as home_goals,
    try_cast("FTAG" as integer)                                 as away_goals,
    nullif(trim("FTR"), '')                                     as result,
    try_cast("HTHG" as integer)                                 as ht_home_goals,
    try_cast("HTAG" as integer)                                 as ht_away_goals,

    try_cast("HS" as integer)                                   as home_shots,
    try_cast("AS" as integer)                                   as away_shots,
    try_cast("HST" as integer)                                  as home_shots_on_target,
    try_cast("AST" as integer)                                  as away_shots_on_target

    {%- for o in odds_sources() %},
    try_cast("{{ o.h }}" as double)                             as {{ o.prefix }}_h,
    try_cast("{{ o.d }}" as double)                             as {{ o.prefix }}_d,
    try_cast("{{ o.a }}" as double)                             as {{ o.prefix }}_a
    {%- endfor %}

from src
