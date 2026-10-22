-- O acidente sobre o traçado, pelo km: entre as duas estações de referência
-- que o cercam, a posição é interpolada em linha reta. Fora da primeira e da
-- última estação de referência não há posição, porque extrapolar a escala de
-- um trecho para o vizinho erra de centenas de metros a quilômetros.
with acidentes as (
    select acidente_id, km_inicial as km
    from {{ ref('int_acidentes__deduplicados') }}
    where ferrovia = 'MRS'
        and linha_ferrea = 'Posto km 64 - 452 (Linha do Centro)'
        and km_inicial is not null
),

ancoras as (
    select km, cadeia_m from {{ ref('int_estacoes__km_linha_jf') }}
),

cercados as (
    select
        a.acidente_id,
        a.km,
        antes.km as km_antes,
        antes.cadeia_m as cadeia_antes,
        depois.km as km_depois,
        depois.cadeia_m as cadeia_depois
    from acidentes a
    cross join lateral (select * from ancoras where km <= a.km order by km desc limit 1) antes
    cross join lateral (select * from ancoras where km > a.km order by km limit 1) depois
)

select
    c.acidente_id,
    c.cadeia_antes + (c.km - c.km_antes) * (c.cadeia_depois - c.cadeia_antes) / (c.km_depois - c.km_antes) as cadeia_m,
    c.km_depois - c.km_antes as vao_entre_ancoras_km,
    st_transform(st_lineinterpolatepoint(
        l.geom,
        (c.cadeia_antes + (c.km - c.km_antes) * (c.cadeia_depois - c.cadeia_antes) / (c.km_depois - c.km_antes)) / l.comprimento_m
    ), 4326) as geom
from cercados c
cross join {{ ref('stg_osm__linha_jf') }} l
