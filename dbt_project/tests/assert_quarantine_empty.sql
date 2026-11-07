{{ config(severity='warn') }}
-- Clean source data should quarantine nothing. A warning here means: go read the reasons.
select * from {{ ref('silver_quarantine_matches') }}
