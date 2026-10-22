-- Trechos de 1 km do km oficial, desenhados sobre o traçado com a mesma
-- interpolação dos acidentes. Um trecho de 1 km oficial não mede 1 km no
-- traçado: entre o Posto km 271 e Juiz de Fora, por exemplo, mede mais. Entra
-- o trecho cujo meio cai dentro de Juiz de Fora (a união dos setores
-- censitários).
with kms as (
    select k::numeric as km, k as trecho_km
    from generate_series(
        (select ceil(min(km))::int from {{ ref('int_estacoes__km_linha_jf') }}),
        (select floor(max(km))::int - 1 from {{ ref('int_estacoes__km_linha_jf') }})
    ) k
),

inicio as ({{ km_no_tracado_jf('kms', 'km') }}),

fim_kms as (select km + 1 as km, trecho_km from kms),

fim as ({{ km_no_tracado_jf('fim_kms', 'km') }}),

trechos as (
    select
        i.trecho_km,
        i.cadeia_m as cadeia_inicio_m,
        f.cadeia_m as cadeia_fim_m,
        greatest(i.vao_entre_ancoras_km, f.vao_entre_ancoras_km) as vao_entre_ancoras_km,
        st_linesubstring(l.geom, i.cadeia_m / l.comprimento_m, f.cadeia_m / l.comprimento_m) as geom
    from inicio i
    join fim f using (trecho_km)
    cross join {{ ref('stg_osm__linha_jf') }} l
),

municipio as (
    select st_union(geom) as geom from {{ ref('stg_ibge__setores_jf') }}
)

select
    t.trecho_km,
    t.cadeia_inicio_m,
    t.cadeia_fim_m,
    st_length(t.geom) as comprimento_m,
    t.vao_entre_ancoras_km,
    t.geom
from trechos t
cross join municipio m
where st_within(st_lineinterpolatepoint(t.geom, 0.5), m.geom)
