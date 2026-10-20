-- O CSV de 2019 traz dezembro da RMS duas vezes: 34 registros repetidos com
-- os mesmos valores. Repetição idêntica sai aqui. Uma repetição com valores
-- diferentes passaria pelo distinct e o teste de chave única do fato pararia
-- o pipeline, porque aí não há como saber qual das duas vale.
select distinct
    mes,
    ferrovia,
    mercadoria_antt,
    estacao_origem,
    uf_origem,
    estacao_destino,
    uf_destino,
    tu,
    tku
from {{ ref('stg_antt__producao') }}
