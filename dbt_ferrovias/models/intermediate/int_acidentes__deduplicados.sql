-- O arquivo de 2004 a 2020 registra 29 acidentes duas ou três vezes: mesma
-- ferrovia, data, hora, quilômetro e trem, com o prefixo digitado de outro
-- jeito ("K- 01" e "K--01") e um campo preenchido numa cópia e vazio na
-- outra. Nenhuma das cópias diverge no número de óbitos. Fica a cópia com
-- mais campos preenchidos.
with chaveados as (
    select
        *,
        row_number() over (
            partition by
                ferrovia, data_ocorrencia, hora_ocorrencia, km_inicial,
                regexp_replace(upper(coalesce(prefixo, '')), '[^A-Z0-9]', '', 'g')
            order by
                (causa_direta <> 'Não informada')::int
                + (natureza <> 'Não informada')::int
                + (estacao_anterior is not null)::int
                + (estacao_posterior is not null)::int
                + (municipio is not null)::int desc,
                arquivo,
                linha
        ) as copia
    from {{ ref('stg_antt__acidentes') }}
)

select * from chaveados where copia = 1
