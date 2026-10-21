-- Para cada porto, produto e mês: quanto foi exportado, quanto chegou de trem
-- e a diferença, que é a carga que chegou por outro meio (para esses produtos
-- em Santos, caminhão). Só entram os meses que as duas fontes já publicaram.
with exportado as (
    select e.mes, p.porto, pr.produto, sum(e.toneladas) as exportado_t
    from {{ ref('stg_comex__exportacao') }} e
    join {{ ref('portos') }} p on p.urf = e.urf
    join {{ ref('produtos_exportacao') }} pr on pr.sh4 = e.sh4
    group by 1, 2, 3
),

trilho as (
    select mes, porto, produto, sum(tu) as trilho_t
    from {{ ref('int_trilho__chegadas_porto') }}
    group by 1, 2, 3
),

ate as (
    select least(
        (select max(mes) from {{ ref('stg_comex__exportacao') }}),
        (select max(mes) from {{ ref('fct_producao_mensal') }})
    ) as mes
)

-- Full join: trilho sem exportação correspondente aparece com exportado 0, em
-- vez de sumir. Foi assim que o teste de coerência deixou passar, de início,
-- uma posição SH4 que o Comex Stat não tinha baixado.
select
    mes,
    porto,
    produto,
    round(coalesce(e.exportado_t, 0)) as exportado_t,
    round(coalesce(t.trilho_t, 0)) as trilho_t,
    round(coalesce(e.exportado_t, 0) - coalesce(t.trilho_t, 0)) as fora_do_trilho_t
from exportado e
full join trilho t using (mes, porto, produto)
where mes >= '2015-01-01' and mes <= (select mes from ate)
