select
    mes,
    ferrovia,
    grupo,
    sum(tu)::bigint as tu,
    sum(tku)::bigint as tku
from {{ ref('fct_producao_mensal') }}
group by 1, 2, 3
