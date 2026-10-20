select
    arquivo,
    linha,
    to_date('01/' || mes_ano, 'DD/MM/YYYY') as mes,
    ferrovia,
    mercadoria as mercadoria_antt,
    estacao_origem,
    uf_origem,
    estacao_destino,
    uf_destino,
    -- Número no padrão brasileiro, sempre inteiro: "16.578.555".
    replace(tu, '.', '')::bigint as tu,
    replace(tku, '.', '')::bigint as tku
from {{ source('antt', 'producao') }}
