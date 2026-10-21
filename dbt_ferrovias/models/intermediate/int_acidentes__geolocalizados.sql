-- O acidente não tem coordenada, só o quilômetro na linha e as estações entre
-- as quais ocorreu. O ponto no mapa é o pátio da estação anterior (ou da
-- posterior, quando a anterior não casa), pelas mesmas regras de nome das
-- estações do SIADE: mesma UF, ou mesma ferrovia nas estações de divisa.
with lados as (
    select acidente_id, ferrovia, uf, estacao_anterior as estacao, 1 as lado
    from {{ ref('int_acidentes__deduplicados') }}
    where estacao_anterior is not null
    union all
    select acidente_id, ferrovia, uf, estacao_posterior, 2
    from {{ ref('int_acidentes__deduplicados') }}
    where estacao_posterior is not null
),

candidatos as (
    select
        l.acidente_id,
        l.estacao,
        l.lado,
        p.lat,
        p.lon,
        row_number() over (
            partition by l.acidente_id
            order by l.lado, (p.uf = l.uf) desc, (p.ferrovia = l.ferrovia) desc, p.patio_id
        ) as ordem
    from lados l
    join {{ ref('stg_infrasa__patios') }} p
        on p.nome_normalizado = {{ normalizar_nome('l.estacao') }}
       and (p.uf = l.uf or p.ferrovia = l.ferrovia)
)

select
    a.*,
    c.lat,
    c.lon,
    case c.lado when 1 then 'estação anterior' when 2 then 'estação posterior' end as local_no_mapa
from {{ ref('int_acidentes__deduplicados') }} a
left join candidatos c on c.acidente_id = a.acidente_id and c.ordem = 1
