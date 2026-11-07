{#
  Rolling form of every team BEFORE each of its matches. One row per (match_id, team_id).

  Leakage rule: every window ends at "1 preceding", so the current match is never inside it.
  The windows run over the team's whole history (not per season), so at the start of a season
  they still reach back into the previous one. n_prev_10 says how many matches were really in
  the window (0 to 10); season_start_flag marks rows where the window is not yet filled by
  matches of the current season.

  tests/test_leakage.py renders this file with jinja2 and runs it on truncated data, so it may
  only use `ref` and `config` (no vars, no macros).
#}
{{ config(materialized='view', schema='staging') }}

with tm as (

    select * from {{ ref('silver_team_matches') }}

),

windows as (

    select
        match_id,
        team_id,
        match_date,
        season,
        is_home,

        count(*)                                        over w10 as n_prev_10,
        avg(points)                                     over w10 as ppg_10,
        avg(goals_for)                                  over w10 as gf_10,
        avg(goals_against)                              over w10 as ga_10,
        avg(goals_for - goals_against)                  over w10 as gd_10,
        avg(case when points = 3 then 1.0 else 0.0 end) over w10 as win_rate_10,
        avg(points)                                     over w5  as ppg_5,
        avg(goals_for - goals_against)                  over w5  as gd_5,
        avg(points)                                     over w10_venue as ppg_10_venue,

        avg(shots_for)                                  over w10 as shots_for_10,
        avg(sot_for)                                    over w10 as sot_for_10,
        avg(shots_against)                              over w10 as shots_against_10,
        avg(sot_against)                                over w10 as sot_against_10,

        date_diff('day', lag(match_date) over w_all, match_date) as rest_days,
        count(*) over w_season                          as matchday_proxy
    from tm
    window
        w10        as (partition by team_id
                       order by match_date, match_id
                       rows between 10 preceding and 1 preceding),
        w5         as (partition by team_id
                       order by match_date, match_id
                       rows between 5 preceding and 1 preceding),
        -- same venue only: for a home match, the previous HOME matches of that team
        w10_venue  as (partition by team_id, is_home
                       order by match_date, match_id
                       rows between 10 preceding and 1 preceding),
        w_all      as (partition by team_id
                       order by match_date, match_id),
        w_season   as (partition by team_id, season
                       order by match_date, match_id
                       rows between unbounded preceding and 1 preceding)

),

-- how many matches the team played in the 14 days BEFORE this match (strictly earlier dates)
load_14d as (

    select
        a.match_id,
        a.team_id,
        count(b.match_id) as matches_last_14d
    from tm a
    left join tm b
        on  b.team_id = a.team_id
        and b.match_date <  a.match_date
        and b.match_date >= cast(a.match_date - interval 14 day as date)
    group by a.match_id, a.team_id

),

-- "promoted": the team did not play in the previous season (new to the data after the first
-- season, or coming back after at least one season away). Known before the season starts.
team_seasons as (

    select distinct
        team_id,
        season,
        cast(left(season, 4) as integer) as season_year
    from tm

),

promoted as (

    select
        team_id,
        season,
        (
            (lag(season_year) over (partition by team_id order by season_year) is null
                and season_year > min(season_year) over ())
            or
            (lag(season_year) over (partition by team_id order by season_year) < season_year - 1)
        ) as is_promoted
    from team_seasons

)

select
    w.match_id,
    w.team_id,
    w.match_date,
    w.season,
    w.is_home,
    w.n_prev_10,
    w.ppg_10,
    w.gf_10,
    w.ga_10,
    w.gd_10,
    w.win_rate_10,
    w.ppg_5,
    w.gd_5,
    w.ppg_10_venue,
    w.shots_for_10,
    w.sot_for_10,
    w.shots_against_10,
    w.sot_against_10,
    w.rest_days,
    l.matches_last_14d,
    w.matchday_proxy,
    (w.matchday_proxy < 10) as season_start_flag,
    coalesce(p.is_promoted, false) as is_promoted
from windows w
inner join load_14d l using (match_id, team_id)
left join promoted p using (team_id, season)
order by w.match_date, w.match_id, w.team_id
