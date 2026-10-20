-- Um mês que some do CSV não dá erro de carga, só um buraco no gráfico.
with meses as (
    select generate_series(
        '2006-01-01'::date,
        (select max(mes) from {{ ref('fct_producao_mensal') }}),
        interval '1 month'
    )::date as mes
)

select m.mes
from meses m
left join {{ ref('fct_producao_mensal') }} f on f.mes = m.mes and f.ferrovia = 'MRS'
where f.mes is null
