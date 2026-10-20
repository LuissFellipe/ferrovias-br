-- Uma rota tem sempre a mesma extensão de trilho, então TKU / TU deveria
-- repetir todo mês. Medido em out/2026: 93% da carga fica a menos de 1% da
-- mediana da própria rota e 0,03% desvia mais de 50% (ex.: Intendente Câmara
-- → Curuputuba com 1.198 km em 2006 contra 732 km de mediana). O resíduo é
-- erro de digitação na origem e não tem como ser corrigido aqui; o teste
-- falha se ele crescer para mais de 0,5% da carga, o que indicaria TU e TKU
-- trocados ou uma unidade nova num arquivo.
with mediana as (
    select
        ferrovia,
        origem_id,
        destino_id,
        percentile_cont(0.5) within group (order by distancia_km) as mediana_km,
        count(*) as meses
    from {{ ref('fct_producao_mensal') }}
    where tu > 0
    group by 1, 2, 3
),

fluxos as (
    select f.tu, abs(f.distancia_km - m.mediana_km) / nullif(m.mediana_km, 0) as desvio
    from {{ ref('fct_producao_mensal') }} f
    join mediana m using (ferrovia, origem_id, destino_id)
    where f.tu > 0 and m.meses >= 6
)

select sum(tu) filter (where desvio > 0.5) as tu_fora, sum(tu) as tu_total
from fluxos
having sum(tu) filter (where desvio > 0.5) > 0.005 * sum(tu)
