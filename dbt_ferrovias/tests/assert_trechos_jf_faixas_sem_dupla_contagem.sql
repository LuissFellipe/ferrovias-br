-- Cada lugar deve contar para um trecho só. A faixa de cada trecho tem a ponta
-- reta, mas nas curvas as faixas vizinhas ainda se sobrepõem: em 22/10/2026 a
-- soma por trecho passava em 3,5% a população da faixa da linha inteira; com a
-- ponta redonda, este teste falha. Falha acima de 5%.
with faixa as (
    select st_union(st_buffer(st_transform(geom, 31983), 500, 'endcap=flat')) as geom
    from {{ ref('fct_trechos_jf') }}
),

linha_inteira as (
    select sum(s.pessoas * st_area(st_intersection(s.geom, f.geom)) / s.area_m2) as pessoas
    from {{ ref('stg_ibge__setores_jf') }} s, faixa f
    where st_intersects(s.geom, f.geom)
),

por_trecho as (
    select sum(pessoas_500m) as pessoas from {{ ref('fct_trechos_jf') }}
)

select l.pessoas as linha_inteira, t.pessoas as soma_dos_trechos
from linha_inteira l, por_trecho t
where abs(t.pessoas / l.pessoas - 1) > 0.05
