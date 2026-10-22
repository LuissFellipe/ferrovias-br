-- O acidente sobre o traçado, pelo km (ver a macro km_no_tracado_jf).
with acidentes as (
    select acidente_id, km_inicial as km
    from {{ ref('int_acidentes__deduplicados') }}
    where ferrovia = 'MRS'
        and linha_ferrea = 'Posto km 64 - 452 (Linha do Centro)'
        and km_inicial is not null
),

posicionados as (
    {{ km_no_tracado_jf('acidentes', 'km') }}
)

select
    p.acidente_id,
    p.cadeia_m,
    p.vao_entre_ancoras_km,
    st_transform(st_lineinterpolatepoint(l.geom, p.cadeia_m / l.comprimento_m), 4326) as geom
from posicionados p
cross join {{ ref('stg_osm__linha_jf') }} l
