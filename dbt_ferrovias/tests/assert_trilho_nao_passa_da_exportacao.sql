-- O trem leva a carga até o porto; o Comex Stat conta o que embarcou. Num ano
-- inteiro, o trilho não pode trazer muito mais do que o porto exportou do
-- mesmo produto. A folga de 10% cobre carga que chega em dezembro e embarca
-- em janeiro: o máximo medido de 2015 a 2025 foi o milho em 2021 (102%), ano
-- de safrinha frustrada. Acima disso, uma estação foi contada como porto sem
-- ser, ou uma mercadoria do SIADE foi casada com a posição SH4 errada.
select
    extract(year from mes)::int as ano,
    porto,
    produto,
    sum(trilho_t) as trilho_t,
    sum(exportado_t) as exportado_t
from {{ ref('fct_porto_produto_mensal') }}
group by 1, 2, 3
having count(*) = 12 and sum(trilho_t) > 1.10 * sum(exportado_t)
