{# Põe um km da Linha do Centro no traçado de Juiz de Fora: entre as duas
   estações de referência que o cercam, a posição é interpolada em linha reta.
   Devolve as colunas de `relacao` mais cadeia_m (metros desde o começo do
   traçado) e vao_entre_ancoras_km. Fora da primeira e da última estação não
   há posição: extrapolar a escala de um trecho para o vizinho erra de
   centenas de metros a quilômetros. #}
{% macro km_no_tracado_jf(relacao, coluna_km) -%}
    select
        r.*,
        antes.cadeia_m + (r.{{ coluna_km }} - antes.km) * (depois.cadeia_m - antes.cadeia_m) / (depois.km - antes.km) as cadeia_m,
        depois.km - antes.km as vao_entre_ancoras_km
    from {{ relacao }} r
    cross join lateral (
        select km, cadeia_m from {{ ref('int_estacoes__km_linha_jf') }}
        where km <= r.{{ coluna_km }} order by km desc limit 1
    ) antes
    cross join lateral (
        select km, cadeia_m from {{ ref('int_estacoes__km_linha_jf') }}
        where km > r.{{ coluna_km }} order by km limit 1
    ) depois
{%- endmacro %}
