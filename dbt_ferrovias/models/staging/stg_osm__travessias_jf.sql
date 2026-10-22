{{ config(materialized='table') }}

-- Lugares onde se cruza a linha principal em nível. O OSM marca poucas
-- passagens como passagem: no centro, a maioria das ruas cruza a linha sem nó
-- marcado. Então valem também os pontos onde uma rua ou caminho corta o
-- traçado, desde que não seja ponte nem túnel.
--
-- Isto NÃO serve para validar a posição dos acidentes. Medi a distância do
-- acidente em passagem em nível até a travessia mais próxima com os acidentes
-- deslocados de -1 km a +1 km: a mediana ficou entre 79 e 178 m em todos os
-- deslocamentos, e a melhor foi com +300 m. No centro há uma travessia a cada
-- 200–300 m, então qualquer posição cai perto de alguma.
with linha as (select geom from {{ ref('stg_osm__linha_jf') }}),

nos as (
    select 'nó ' || (tags->>'railway') as origem, st_transform(geom, 31983) as geom
    from {{ source('osm', 'osm_jf') }}
    where tipo = 'node' and tags->>'railway' in ('level_crossing', 'crossing')
),

ruas as (
    select 'rua (' || (r.tags->>'highway') || ')' as origem,
           (st_dump(st_intersection(st_transform(r.geom, 31983), l.geom))).geom as geom
    from {{ source('osm', 'osm_jf') }} r, linha l
    where r.tipo = 'way'
        and r.tags ? 'highway'
        and coalesce(r.tags->>'bridge', 'no') = 'no'
        and coalesce(r.tags->>'tunnel', 'no') = 'no'
        and coalesce(r.tags->>'layer', '0') = '0'
        and st_intersects(st_transform(r.geom, 31983), l.geom)
)

select t.origem, st_linelocatepoint(l.geom, t.geom) * l.comprimento_m as cadeia_m
from (select * from nos union all select * from ruas) t, {{ ref('stg_osm__linha_jf') }} l
where st_dwithin(t.geom, l.geom, 15)
