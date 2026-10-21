-- O que chega de trem a cada porto: todo fluxo, de qualquer concessionária,
-- cujo destino é uma estação dentro do raio do porto. Pelo raio, e não por
-- uma lista de estações, para que um terminal novo que a ANTT passe a
-- informar entre sozinho.
select
    f.mes,
    p.porto,
    pr.produto,
    f.ferrovia,
    o.uf as uf_origem,
    f.tu,
    f.tku
from {{ ref('fct_producao_mensal') }} f
join {{ ref('produtos_exportacao') }} pr on pr.mercadoria_antt = f.mercadoria_antt
join {{ ref('dim_estacoes') }} d on d.estacao_id = f.destino_id and d.geolocalizada
join {{ ref('dim_estacoes') }} o on o.estacao_id = f.origem_id
join {{ ref('portos') }} p
    on st_distancesphere(st_makepoint(d.lon, d.lat), st_makepoint(p.lon, p.lat)) <= p.raio_km * 1000
