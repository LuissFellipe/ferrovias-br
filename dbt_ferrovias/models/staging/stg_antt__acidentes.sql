-- Um acidente por linha, tipado. A data depende do arquivo: no de dezembro de
-- 2020 em diante, as datas com dia até 12 vieram como MM/DD (ver
-- ingest_acidentes.py, que detecta o formato pela ordem do arquivo).
with base as (
    select a.*, f.formato_data, f.periodo_inicio, f.periodo_fim
    from {{ source('antt', 'acidentes') }} a
    join {{ source('antt', 'acidentes_arquivos') }} f using (arquivo)
)

select
    md5(arquivo || ':' || linha) as acidente_id,
    arquivo,
    linha,
    periodo_inicio as arquivo_inicio,
    periodo_fim as arquivo_fim,
    case
        when formato_data = 'misto' and split_part(data_ocorrencia, '/', 1)::int <= 12
            then to_date(data_ocorrencia, 'MM/DD/YYYY')
        else to_date(data_ocorrencia, 'DD/MM/YYYY')
    end as data_ocorrencia,
    case when hora_ocorrencia ~ '^([01]?\d|2[0-3]):[0-5]\d$' then hora_ocorrencia::time end as hora_ocorrencia,
    ferrovia,
    gravidade = 'Sim' as grave,
    nullif(uf, '') as uf,
    municipio,
    linha_ferrea,
    km_inicial::numeric as km_inicial,
    km_final::numeric as km_final,
    estacao_anterior,
    estacao_posterior,
    -- O layout novo detalha a natureza ("Abalroamento em passagem em nível").
    -- A natureza básica é a mesma nos dois layouts; a passagem em nível já
    -- tem coluna própria desde 2004.
    coalesce(
        regexp_replace(natureza, '\s+(em|fora de|com|entre)\s.*$', ''),
        'Não informada'
    ) as natureza,
    natureza as natureza_detalhada,
    case
        when causa_direta is null then 'Não informada'
        when causa_direta = 'Força maior' then 'Casos Fortuitos ou de Força Maior'
        else causa_direta
    end as causa_direta,
    causa_contributiva,
    passagem_em_nivel = 'Sim' as em_passagem_em_nivel,
    -- Horas de circulação interrompida.
    interrupcao::numeric as interrupcao_h,
    n_trens::int as n_trens,
    prefixo,
    servico_transporte,
    feridos::numeric::int as feridos,
    obitos::numeric::int as obitos,
    mercadoria,
    outra_ferrovia,
    -- Só no layout novo, em reais, com vírgula decimal e sem separador de milhar.
    replace(prejuizo, ',', '.')::numeric as prejuizo_rs
from base
