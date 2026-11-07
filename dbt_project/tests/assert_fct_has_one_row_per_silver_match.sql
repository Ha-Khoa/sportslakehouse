-- An inner join that silently drops matches would shrink the training data without any error.
select s.n_silver, f.n_fct
from (select count(*) as n_silver from {{ ref('silver_matches') }}) s
cross join (select count(*) as n_fct from {{ ref('fct_match_features') }}) f
where s.n_silver <> f.n_fct
