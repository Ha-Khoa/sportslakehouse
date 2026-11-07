{#
  One place that lists which odds columns we use, from which bookmaker, open or closing.
  Staging casts these columns; silver_match_odds turns them into one row per
  (match, bookmaker, open/closing).
  Which seasons have which column: see docs/data_profile.md (Bet365 opening from 2002-03,
  Pinnacle 2012-13 to 2025-26, Bet365 closing and market average from 2019-20).
#}
{% macro odds_sources() %}
    {{ return([
        {'bookmaker': 'bet365',     'is_closing': false, 'prefix': 'bet365_open',    'h': 'B365H',  'd': 'B365D',  'a': 'B365A'},
        {'bookmaker': 'bet365',     'is_closing': true,  'prefix': 'bet365_close',   'h': 'B365CH', 'd': 'B365CD', 'a': 'B365CA'},
        {'bookmaker': 'pinnacle',   'is_closing': false, 'prefix': 'pinnacle_open',  'h': 'PSH',    'd': 'PSD',    'a': 'PSA'},
        {'bookmaker': 'pinnacle',   'is_closing': true,  'prefix': 'pinnacle_close', 'h': 'PSCH',   'd': 'PSCD',   'a': 'PSCA'},
        {'bookmaker': 'market_avg', 'is_closing': false, 'prefix': 'avg_open',       'h': 'AvgH',   'd': 'AvgD',   'a': 'AvgA'},
        {'bookmaker': 'market_avg', 'is_closing': true,  'prefix': 'avg_close',      'h': 'AvgCH',  'd': 'AvgCD',  'a': 'AvgCA'}
    ]) }}
{% endmacro %}
