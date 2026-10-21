-- Acidentes por ferrovia e ano, contra o TKU dos mesmos meses. O índice
-- oficial da ANTT divide por trem·km, que não é dado aberto; aqui o
-- denominador é o TKU do SIADE, e o índice oficial vem ao lado até onde ele
-- foi publicado.
--
-- O ano só vale até o último mês que as duas fontes cobrem: em 2026 os
-- acidentes vão até janeiro e a produção até agosto, e dividir um mês de
-- acidentes por oito de carga daria um índice oito vezes menor.
--
-- Atenção: o acidente é da concessionária dona do trecho; o TKU, da
-- concessionária responsável pelo fluxo, que pode rodar em malha alheia.
with limite as (
    select least(
        (select max(arquivo_fim) from {{ ref('stg_antt__acidentes') }}),
        (select (max(mes) + interval '1 month' - interval '1 day')::date from {{ ref('fct_producao_mensal') }})
    ) as ultimo_dia
),

acidentes as (
    select
        ferrovia,
        ano,
        count(*) as acidentes,
        count(*) filter (where grave) as graves,
        count(*) filter (where em_passagem_em_nivel) as em_passagem_em_nivel,
        count(*) filter (where natureza = 'Atropelamento') as atropelamentos,
        count(*) filter (where natureza = 'Descarrilamento') as descarrilamentos,
        sum(obitos) as obitos,
        sum(feridos) as feridos
    from {{ ref('fct_acidentes') }}
    where data_ocorrencia <= (select ultimo_dia from limite)
    group by 1, 2
),

carga as (
    select ferrovia, extract(year from mes)::int as ano, sum(tku) as tku, count(distinct mes) as meses
    from {{ ref('fct_producao_mensal') }}
    where mes <= (select ultimo_dia from limite)
    group by 1, 2
)

select
    coalesce(a.ferrovia, c.ferrovia) as ferrovia,
    coalesce(a.ano, c.ano) as ano,
    coalesce(c.meses, 0) as meses_de_carga,
    coalesce(a.acidentes, 0) as acidentes,
    coalesce(a.graves, 0) as graves,
    coalesce(a.em_passagem_em_nivel, 0) as em_passagem_em_nivel,
    coalesce(a.atropelamentos, 0) as atropelamentos,
    coalesce(a.descarrilamentos, 0) as descarrilamentos,
    coalesce(a.obitos, 0) as obitos,
    coalesce(a.feridos, 0) as feridos,
    c.tku,
    round(1e9 * coalesce(a.acidentes, 0) / nullif(c.tku, 0), 2) as acidentes_por_bilhao_tku,
    round(1e9 * coalesce(a.graves, 0) / nullif(c.tku, 0), 2) as graves_por_bilhao_tku,
    i.indice_por_milhao_trem_km as indice_oficial
from acidentes a
full join carga c on c.ferrovia = a.ferrovia and c.ano = a.ano
left join {{ ref('stg_antt__indice_acidentes') }} i
    on i.ferrovia = coalesce(a.ferrovia, c.ferrovia) and i.ano = coalesce(a.ano, c.ano)
-- A produção começa em 2006; antes disso não há denominador.
where coalesce(a.ano, c.ano) >= 2006
