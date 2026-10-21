-- Um acidente por linha, sem dado pessoal: a ingestão já descarta o nome do
-- maquinista, e o texto livre de perímetro urbano fica no staging.
select
    acidente_id,
    data_ocorrencia,
    extract(year from data_ocorrencia)::int as ano,
    date_trunc('month', data_ocorrencia)::date as mes,
    hora_ocorrencia,
    ferrovia,
    grave,
    natureza,
    natureza_detalhada,
    causa_direta,
    causa_contributiva,
    -- Até 2009 o registro só tem acidentes graves e nenhum óbito no país
    -- inteiro, com 130 a 190 atropelamentos por ano; 2010 é a transição. Só a
    -- partir de 2011 um ano se compara com outro.
    extract(year from data_ocorrencia) >= 2011 as registro_completo,
    -- A classificação de causas mudou com o arquivo de dezembro de 2020.
    case when arquivo_inicio < '2020-12-01' then 'até nov/2020' else 'desde dez/2020' end as taxonomia_causa,
    em_passagem_em_nivel,
    uf,
    municipio,
    linha_ferrea,
    km_inicial,
    estacao_anterior,
    estacao_posterior,
    lat,
    lon,
    local_no_mapa,
    obitos,
    feridos,
    interrupcao_h,
    prejuizo_rs,
    servico_transporte,
    mercadoria,
    outra_ferrovia
from {{ ref('int_acidentes__geolocalizados') }}
