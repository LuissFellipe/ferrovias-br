-- Cada ano do índice vem do arquivo mais novo que o tem. O arquivo "de 2006 a
-- 2025" foi publicado vazio, e o de 2019 continua no portal.
with linhas as (
    select
        i.concessionaria as ferrovia,
        i.ano::int as ano,
        replace(i.indice, ',', '.')::numeric as indice_por_milhao_trem_km,
        i.arquivo,
        row_number() over (
            partition by i.concessionaria, i.ano
            order by f.ano_final desc, f.modificado_em desc
        ) as ordem
    from {{ source('antt', 'indice_acidentes') }} i
    join {{ source('antt', 'indice_acidentes_arquivos') }} f using (arquivo)
)

select ferrovia, ano, indice_por_milhao_trem_km, arquivo
from linhas
where ordem = 1
