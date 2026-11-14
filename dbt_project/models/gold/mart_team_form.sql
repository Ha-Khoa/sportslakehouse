{#
  Form of every team AS OF the end of each of its match days, for the dashboard and the API.
  Grain (team_id, match_date). Unlike int_team_form (form BEFORE a match, used for ML), this
  one INCLUDES the match played that day, because it answers "how is the team doing now?".
  Never join this table to the ML features: it contains the current match (leakage).
#}
{{ config(
    materialized='external',
    format='parquet',
    location=var('lake_dir') ~ '/gold/mart_team_form.parquet'
) }}

with tm as (

    select
        team_id,
        match_date,
        match_id,
        points,
        goals_for,
        goals_against,
        case points when 3 then 'W' when 1 then 'D' else 'L' end as result_letter
    from {{ ref('silver_team_matches') }}

)

select
    team_id,
    match_date,
    count(*)                                         over w10 as n_matches_in_window,
    avg(points)                                      over w10 as ppg_10,
    avg(goals_for)                                   over w10 as gf_10,
    avg(goals_against)                               over w10 as ga_10,
    avg(goals_for - goals_against)                   over w10 as gd_10,
    avg(case when points = 3 then 1.0 else 0.0 end)  over w10 as win_rate_10,
    -- last 5 results, oldest to newest, e.g. 'WWDLW' (concat ignores NULLs at the start)
    concat(
        lag(result_letter, 4) over w_all,
        lag(result_letter, 3) over w_all,
        lag(result_letter, 2) over w_all,
        lag(result_letter, 1) over w_all,
        result_letter
    )                                                as last_5
from tm
window
    w10   as (partition by team_id order by match_date, match_id
              rows between 9 preceding and current row),
    w_all as (partition by team_id order by match_date, match_id)
order by team_id, match_date
