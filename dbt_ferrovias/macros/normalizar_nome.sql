{# Deixa só o que identifica a estação: sem acento, sem caixa e com as
   abreviações por extenso, porque o SIADE escreve "Eng. Neiva" onde a camada
   de pátios escreve "Engenheiro Neiva". #}
{% macro normalizar_nome(coluna) -%}
    trim(regexp_replace(
        regexp_replace(regexp_replace(regexp_replace(regexp_replace(
            lower(unaccent({{ coluna }})),
            '\meng\M\.?\s*', 'engenheiro ', 'g'),
            '\mdr\M\.?\s*', 'doutor ', 'g'),
            '\mcel\M\.?\s*', 'coronel ', 'g'),
            '\mpres\M\.?\s*', 'presidente ', 'g'),
        '[^a-z0-9]+', ' ', 'g'))
{%- endmacro %}
