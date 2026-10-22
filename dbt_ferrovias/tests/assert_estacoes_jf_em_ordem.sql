-- O km cresce na mesma direção do traçado. Uma estação casada com o pátio
-- errado, ou o traçado invertido, aparece aqui como estação fora de ordem.
select estacao, km, cadeia_m
from (
    select *, lag(cadeia_m) over (order by km) as cadeia_anterior
    from {{ ref('int_estacoes__km_linha_jf') }}
) e
where cadeia_m <= cadeia_anterior
