-- A mesma conta aberta por estado, por ano. É uma aproximação: no Comex Stat
-- a UF é a de produção, e no SIADE é a da estação onde a carga embarcou no
-- trem. Soja de Goiás que vai de caminhão até um terminal em Minas aparece
-- como exportação de GO e como trilho de MG.
with exportado as (
    select extract(year from e.mes)::int as ano, p.porto, pr.produto, e.uf, sum(e.toneladas) as exportado_t
    from {{ ref('stg_comex__exportacao') }} e
    join {{ ref('portos') }} p on p.urf = e.urf
    join {{ ref('produtos_exportacao') }} pr on pr.sh4 = e.sh4
    where e.uf is not null
    group by 1, 2, 3, 4
),

trilho as (
    select extract(year from mes)::int as ano, porto, produto, uf_origem as uf, sum(tu) as trilho_t
    from {{ ref('int_trilho__chegadas_porto') }}
    group by 1, 2, 3, 4
),

anos_completos as (
    -- Só anos fechados nas duas fontes, para não comparar meses diferentes.
    select ano
    from (
        select extract(year from mes)::int as ano, count(distinct mes) as meses
        from {{ ref('fct_porto_produto_mensal') }}
        group by 1
    ) a
    where meses = 12
)

select
    coalesce(e.ano, t.ano) as ano,
    coalesce(e.porto, t.porto) as porto,
    coalesce(e.produto, t.produto) as produto,
    coalesce(e.uf, t.uf) as uf,
    round(coalesce(e.exportado_t, 0)) as exportado_t,
    round(coalesce(t.trilho_t, 0)) as trilho_t
from exportado e
full join trilho t using (ano, porto, produto, uf)
where coalesce(e.ano, t.ano) in (select ano from anos_completos)
