{#
  Long format: one row per (match, bookmaker, open/closing). A row exists only when all three
  odds (home, draw, away) are present, so seasons without a given bookmaker simply have no rows.
  The list of columns comes from the odds_sources() macro.
#}
{{ config(
    materialized='external',
    format='parquet',
    location=var('lake_dir') ~ '/silver/match_odds.parquet',
    alias='match_odds'
) }}

with valid as (

    select * from {{ ref('int_matches_checked') }}
    where quarantine_reason is null

)

{% for o in odds_sources() %}
select
    match_id,
    '{{ o.bookmaker }}'                           as bookmaker,
    {{ 'true' if o.is_closing else 'false' }}     as is_closing,
    {{ o.prefix }}_h                              as odds_home,
    {{ o.prefix }}_d                              as odds_draw,
    {{ o.prefix }}_a                              as odds_away
from valid
where {{ o.prefix }}_h is not null
  and {{ o.prefix }}_d is not null
  and {{ o.prefix }}_a is not null
{% if not loop.last %}union all{% endif %}
{% endfor %}
