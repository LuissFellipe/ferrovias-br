-- Um trecho de 1 km da linha em Juiz de Fora por linha: quantos acidentes
-- teve de 2011 a 2025 e quem vive e o que funciona a até 500 m dele.
--
-- Quem mora não é quem circula: o centro de Juiz de Fora é comercial. Os
-- endereços de comércio e serviço do CNEFE são o indicador de movimento
-- durante o dia, e as escolas do INEP, de onde há crianças.
--
-- A faixa de 500 m (uns 6 minutos a pé) tem a ponta reta, para que cada lugar
-- conte para o trecho em frente a ele e não para os vizinhos. A população de
-- um setor censitário entra na proporção da área dele que cai na faixa, como
-- se as pessoas se espalhassem igualmente pelo setor. Esquerda e direita são
-- no sentido do km crescente (do Rio para Belo Horizonte): um trecho com gente
-- dos dois lados é um trecho que as pessoas precisam atravessar.
with faixas as (
    select
        trecho_km,
        st_buffer(geom, 500, 'endcap=flat') as faixa,
        st_buffer(geom, 500, 'endcap=flat side=left') as esquerda,
        st_buffer(geom, 500, 'endcap=flat side=right') as direita
    from {{ ref('int_trechos_jf') }}
),

populacao as (
    select
        f.trecho_km,
        sum(s.pessoas * st_area(st_intersection(s.geom, f.faixa)) / s.area_m2) as pessoas_500m,
        sum(s.pessoas * st_area(st_intersection(s.geom, f.esquerda)) / s.area_m2) as pessoas_esquerda,
        sum(s.pessoas * st_area(st_intersection(s.geom, f.direita)) / s.area_m2) as pessoas_direita
    from faixas f
    join {{ ref('stg_ibge__setores_jf') }} s on st_intersects(s.geom, f.faixa)
    group by f.trecho_km
),

escolas as (
    select f.trecho_km, count(*) as escolas_500m
    from faixas f
    join {{ ref('stg_inep__escolas_jf') }} e on st_within(e.geom, f.faixa)
    group by f.trecho_km
),

enderecos as (
    select
        f.trecho_km,
        count(*) filter (where d.especie = 'comércio e serviço') as comercio_servico_500m,
        count(*) filter (where d.especie = 'saúde') as saude_500m
    from faixas f
    join {{ ref('stg_ibge__enderecos_jf') }} d on st_within(d.geom, f.faixa)
    group by f.trecho_km
),

travessias as (
    select t.trecho_km, count(*) as travessias_osm
    from {{ ref('int_trechos_jf') }} t
    join {{ ref('stg_osm__travessias_jf') }} x on x.cadeia_m >= t.cadeia_inicio_m and x.cadeia_m < t.cadeia_fim_m
    group by t.trecho_km
),

acidentes as (
    select
        n.trecho_km,
        count(*) as acidentes,
        count(*) filter (where a.natureza = 'Atropelamento') as atropelamentos,
        count(*) filter (where a.natureza = 'Atropelamento' and a.em_passagem_em_nivel) as atropelamentos_em_pn,
        coalesce(sum(a.obitos) filter (where a.natureza = 'Atropelamento'), 0) as obitos_atropelamento,
        coalesce(sum(a.obitos), 0) as obitos
    from {{ ref('fct_acidentes_na_linha_jf') }} n
    join {{ ref('fct_acidentes') }} a using (acidente_id)
    where a.registro_completo
    group by n.trecho_km
)

select
    t.trecho_km,
    t.comprimento_m,
    t.vao_entre_ancoras_km,
    coalesce(p.pessoas_500m, 0) as pessoas_500m,
    coalesce(p.pessoas_esquerda, 0) as pessoas_esquerda,
    coalesce(p.pessoas_direita, 0) as pessoas_direita,
    coalesce(e.escolas_500m, 0) as escolas_500m,
    coalesce(d.comercio_servico_500m, 0) as comercio_servico_500m,
    coalesce(d.saude_500m, 0) as saude_500m,
    coalesce(x.travessias_osm, 0) as travessias_osm,
    coalesce(a.acidentes, 0) as acidentes,
    coalesce(a.atropelamentos, 0) as atropelamentos,
    coalesce(a.atropelamentos_em_pn, 0) as atropelamentos_em_pn,
    coalesce(a.obitos_atropelamento, 0) as obitos_atropelamento,
    coalesce(a.obitos, 0) as obitos,
    st_transform(t.geom, 4326) as geom
from {{ ref('int_trechos_jf') }} t
left join populacao p using (trecho_km)
left join escolas e using (trecho_km)
left join enderecos d using (trecho_km)
left join travessias x using (trecho_km)
left join acidentes a using (trecho_km)
