select
    mes,
    ferrovia,
    grupo,
    sum(tu) as tu,
    sum(tku) as tku
from {{ ref('fct_producao_mensal') }}
group by 1, 2, 3
