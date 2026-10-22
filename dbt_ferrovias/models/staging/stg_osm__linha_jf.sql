-- A linha principal da MRS em Juiz de Fora como um traçado só, em metros
-- (SIRGAS 2000 / UTM 23S). Em graus, a posição ao longo da linha dependeria da
-- direção do trecho: um grau de longitude é 7% mais curto que um de latitude
-- aqui. O traçado começa no sul, porque o km da Linha do Centro cresce do Rio
-- para Belo Horizonte.
with juntada as (
    select (st_dump(st_linemerge(st_union(st_transform(geom, 31983))))).geom as geom
    from {{ source('osm', 'osm_jf') }}
    where tipo = 'way' and tags->>'railway' = 'rail' and tags->>'usage' = 'main'
)

select
    case when st_y(st_startpoint(geom)) > st_y(st_endpoint(geom)) then st_reverse(geom) else geom end as geom,
    st_length(geom) as comprimento_m
from juntada
