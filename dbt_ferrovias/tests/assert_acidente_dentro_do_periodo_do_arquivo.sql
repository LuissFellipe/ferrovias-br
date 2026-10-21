-- Cada arquivo declara no nome o período que cobre. Uma data fora dele é sinal
-- de formato lido errado: foi assim que apareceu o MM/DD do arquivo de
-- dezembro de 2020, que lido como DD/MM começa em "12 de janeiro de 2020".
select acidente_id, arquivo, data_ocorrencia, arquivo_inicio, arquivo_fim
from {{ ref('stg_antt__acidentes') }}
where data_ocorrencia not between arquivo_inicio and arquivo_fim
