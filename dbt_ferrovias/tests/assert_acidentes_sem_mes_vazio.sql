-- O país registra de 20 a 100 acidentes por mês. Um mês sem nenhum é buraco
-- entre dois arquivos da ANTT, não mês seguro.
with meses as (
    select generate_series(
        '2004-01-01'::date,
        (select date_trunc('month', max(arquivo_fim)) from {{ ref('stg_antt__acidentes') }}),
        interval '1 month'
    )::date as mes
)

select m.mes
from meses m
left join {{ ref('fct_acidentes') }} a on a.mes = m.mes
group by m.mes
having count(a.acidente_id) = 0
