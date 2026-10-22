-- O km oficial de cada estação da Linha do Centro em Juiz de Fora, deduzido
-- dos próprios acidentes. Quem registra "entre Juiz de Fora e Mariano
-- Procópio, km 275,864" diz que Juiz de Fora fica antes do km 275,864. O maior
-- km dos acidentes antes da estação e o menor dos acidentes depois dela
-- prendem a estação numa janela: a de Juiz de Fora tem 160 m.
--
-- Não dá para usar o nome dos postos como km: entre o Posto km 261 e o Posto
-- km 271 o traçado mede 7,0 km, e de Cedofeita ao Posto km 271 o km oficial
-- se adianta 2,1 km em relação à distância medida no traçado. Por isso o km
-- é ligado ao traçado estação por estação.
with trechos as (
    select estacao_anterior, estacao_posterior, km_inicial
    from {{ ref('int_acidentes__deduplicados') }}
    where ferrovia = 'MRS'
        and linha_ferrea = 'Posto km 64 - 452 (Linha do Centro)'
        and estacao_anterior is not null
        and estacao_posterior is not null
        and km_inicial is not null
),

janelas as (
    select
        estacao,
        max(km_inicial) filter (where lado = 'antes') as km_min,
        min(km_inicial) filter (where lado = 'depois') as km_max,
        count(*) as acidentes
    from (
        select estacao_posterior as estacao, 'antes' as lado, km_inicial from trechos
        union all
        select estacao_anterior, 'depois', km_inicial from trechos
    ) t
    group by estacao
),

patios as (
    select p.nome, st_transform(st_point(p.lon, p.lat, 4326), 31983) as geom
    from {{ ref('stg_infrasa__patios') }} p
    where p.ferrovia = 'MRS'
)

select
    j.estacao,
    j.km_min,
    j.km_max,
    (j.km_min + j.km_max) / 2 as km,
    j.acidentes,
    st_linelocatepoint(l.geom, p.geom) * l.comprimento_m as cadeia_m,
    st_distance(p.geom, l.geom) as distancia_do_patio_m
from janelas j
join patios p on {{ normalizar_nome('p.nome') }} = {{ normalizar_nome('j.estacao') }}
cross join {{ ref('stg_osm__linha_jf') }} l
-- Só estação presa dos dois lados e com o pátio sobre o traçado do OSM.
where j.km_min < j.km_max
    and st_dwithin(p.geom, l.geom, 100)
