-- Prova física da geolocalização: entre dois pontos, o trilho nunca é mais
-- curto que a linha reta. Uma estação posta no pátio errado aparece aqui
-- como rota "impossível". Hoje 5 das 3.848 rotas passam da tolerância, com
-- menos de 0,01% da carga: a distância informada parece ser só o trecho da
-- própria concessionária. O teste falha se esse resíduo passar de 0,1%.
with rotas as (
    select
        f.origem_id,
        f.destino_id,
        sum(f.tu) as tu,
        sum(f.tku)::numeric / nullif(sum(f.tu), 0) as distancia_ferroviaria_km,
        st_distancesphere(st_makepoint(o.lon, o.lat), st_makepoint(d.lon, d.lat)) / 1000 as linha_reta_km
    from {{ ref('fct_producao_mensal') }} f
    join {{ ref('dim_estacoes') }} o on o.estacao_id = f.origem_id and o.geolocalizada
    join {{ ref('dim_estacoes') }} d on d.estacao_id = f.destino_id and d.geolocalizada
    group by 1, 2, o.lon, o.lat, d.lon, d.lat
),

impossiveis as (
    select sum(tu) as tu
    from rotas
    where linha_reta_km > distancia_ferroviaria_km * 1.1 + 5
)

select i.tu, (select sum(tu) from rotas) as tu_total
from impossiveis i
where i.tu > 0.001 * (select sum(tu) from rotas)
