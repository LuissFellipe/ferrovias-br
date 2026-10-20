-- O SIADE só identifica a estação pelo nome e pela UF. A coordenada vem do
-- pátio de mesmo nome normalizado na mesma UF. Quando há mais de um (nomes
-- como "Santos" se repetem entre concessionárias), vale o pátio da ferrovia
-- que mais movimenta carga na estação. Sem pátio na mesma UF, vale o de mesmo
-- nome e da mesma ferrovia em outra UF: o SIADE e a InfraSA discordam na UF de
-- estações de divisa (Jupiá, MS ou SP; São Simão, GO ou MG). Uma coordenada em
-- seeds/estacoes_manuais.csv tem precedência sobre o pátio.
with pontas as (
    select estacao_origem as estacao, uf_origem as uf, ferrovia, tu
    from {{ ref('int_producao__deduplicada') }}
    union all
    select estacao_destino, uf_destino, ferrovia, tu
    from {{ ref('int_producao__deduplicada') }}
),

por_ferrovia as (
    select estacao, uf, ferrovia, sum(tu) as tu
    from pontas
    group by 1, 2, 3
),

estacoes as (
    select
        estacao,
        uf,
        sum(tu) as tu_total,
        (array_agg(ferrovia order by tu desc, ferrovia))[1] as ferrovia_principal
    from por_ferrovia
    group by 1, 2
),

candidatos as (
    select
        e.estacao,
        e.uf,
        p.patio_id,
        p.lat,
        p.lon,
        p.uf is distinct from e.uf as uf_divergente,
        count(*) over (partition by e.estacao, e.uf) as n_candidatos,
        row_number() over (
            partition by e.estacao, e.uf
            order by
                (p.uf = e.uf) desc nulls last,
                (p.ferrovia = e.ferrovia_principal) desc nulls last,
                p.patio_id
        ) as ordem
    from estacoes e
    join {{ ref('stg_infrasa__patios') }} p
        on p.nome_normalizado = {{ normalizar_nome('e.estacao') }}
       and (p.uf = e.uf or p.ferrovia = e.ferrovia_principal)
)

select
    md5(e.estacao || '|' || e.uf) as estacao_id,
    e.estacao,
    e.uf,
    e.ferrovia_principal,
    e.tu_total,
    c.patio_id,
    coalesce(m.lat, c.lat) as lat,
    coalesce(m.lon, c.lon) as lon,
    case
        when m.lat is not null then 'manual: ' || m.fonte
        when c.uf_divergente then 'InfraSA, pátio em outra UF'
        when c.patio_id is not null then 'InfraSA'
    end as fonte_coordenada,
    coalesce(c.n_candidatos, 0) as n_candidatos
from estacoes e
left join candidatos c
    on c.estacao = e.estacao and c.uf = e.uf and c.ordem = 1
left join {{ ref('estacoes_manuais') }} m
    on m.estacao = e.estacao and m.uf = e.uf
