-- Base do mapa: um fluxo por ano, ferrovia, mercadoria, origem e destino.
select
    extract(year from mes)::int as ano,
    ferrovia,
    mercadoria_antt,
    grupo,
    origem_id,
    destino_id,
    count(*) as meses,
    sum(tu)::bigint as tu,
    sum(tku)::bigint as tku
from {{ ref('fct_producao_mensal') }}
group by 1, 2, 3, 4, 5, 6
