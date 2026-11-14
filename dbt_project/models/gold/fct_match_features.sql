{#
  One row per match: features of the home team (h_), the away team (a_), differences, and the
  label. Everything on the feature side is known BEFORE kick-off (see int_team_form and
  elo_ratings). The columns result, home_goals and away_goals are LABELS: never use them as
  model inputs (leakage test 4, week 3).
  Head-to-head (h2h_*) is from the home team's point of view.
#}
{{ config(
    materialized='external',
    format='parquet',
    location=var('lake_dir') ~ '/gold/fct_match_features.parquet'
) }}

with m as (

    select * from {{ ref('silver_matches') }}

),

form as (

    select * from {{ ref('int_team_form') }}

),

elo as (

    select * from {{ ref('elo_ratings') }}

),

h2h as (

    select * from {{ ref('int_h2h') }}

)

select
    m.match_id,
    m.season,
    m.match_date,
    m.home_team_id,
    m.away_team_id,

    -- home team
    hf.n_prev_10          as h_n_prev_10,
    hf.ppg_10             as h_ppg_10,
    hf.gf_10              as h_gf_10,
    hf.ga_10              as h_ga_10,
    hf.gd_10              as h_gd_10,
    hf.win_rate_10        as h_win_rate_10,
    hf.ppg_5              as h_ppg_5,
    hf.gd_5               as h_gd_5,
    hf.ppg_10_venue       as h_ppg_10_home,      -- form in previous HOME matches only
    hf.shots_for_10       as h_shots_for_10,
    hf.sot_for_10         as h_sot_for_10,
    hf.shots_against_10   as h_shots_against_10,
    hf.sot_against_10     as h_sot_against_10,
    hf.rest_days          as h_rest_days,
    hf.matches_last_14d   as h_matches_last_14d,
    hf.is_promoted        as h_is_promoted,
    he.elo_pre            as h_elo,

    -- away team
    af.n_prev_10          as a_n_prev_10,
    af.ppg_10             as a_ppg_10,
    af.gf_10              as a_gf_10,
    af.ga_10              as a_ga_10,
    af.gd_10              as a_gd_10,
    af.win_rate_10        as a_win_rate_10,
    af.ppg_5              as a_ppg_5,
    af.gd_5               as a_gd_5,
    af.ppg_10_venue       as a_ppg_10_away,      -- form in previous AWAY matches only
    af.shots_for_10       as a_shots_for_10,
    af.sot_for_10         as a_sot_for_10,
    af.shots_against_10   as a_shots_against_10,
    af.sot_against_10     as a_sot_against_10,
    af.rest_days          as a_rest_days,
    af.matches_last_14d   as a_matches_last_14d,
    af.is_promoted        as a_is_promoted,
    ae.elo_pre            as a_elo,

    -- differences (home minus away)
    hf.ppg_10 - af.ppg_10             as ppg_10_diff,
    hf.gd_10  - af.gd_10              as gd_10_diff,
    hf.ppg_5  - af.ppg_5              as ppg_5_diff,
    he.elo_pre - ae.elo_pre           as elo_diff,
    hf.rest_days - af.rest_days       as rest_days_diff,

    -- head-to-head: points of the HOME team in its last (up to) 3 meetings with the away team
    hh.h2h_ppg_last_3,
    hh.h2h_n,

    -- season context
    hf.matchday_proxy                 as matchday_proxy,
    (hf.season_start_flag or af.season_start_flag) as season_start_flag,

    -- labels (never features)
    m.result,
    m.home_goals,
    m.away_goals
from m
inner join form hf on hf.match_id = m.match_id and hf.team_id = m.home_team_id
inner join form af on af.match_id = m.match_id and af.team_id = m.away_team_id
inner join elo  he on he.match_id = m.match_id and he.team_id = m.home_team_id
inner join elo  ae on ae.match_id = m.match_id and ae.team_id = m.away_team_id
inner join h2h  hh on hh.match_id = m.match_id and hh.team_id = m.home_team_id
order by m.match_date, m.match_id
