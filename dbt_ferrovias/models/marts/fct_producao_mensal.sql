select
    p.mes,
    p.ferrovia,
    p.mercadoria_antt,
    m.grupo,
    o.estacao_id as origem_id,
    d.estacao_id as destino_id,
    p.tu,
    p.tku,
    -- TKU / TU é a distância ferroviária média do fluxo no mês.
    round(p.tku::numeric / nullif(p.tu, 0), 1) as distancia_km
from {{ ref('int_producao__deduplicada') }} p
left join {{ ref('dim_mercadorias') }} m using (mercadoria_antt)
join {{ ref('dim_estacoes') }} o on o.estacao = p.estacao_origem and o.uf = p.uf_origem
join {{ ref('dim_estacoes') }} d on d.estacao = p.estacao_destino and d.uf = p.uf_destino
