select
    objectid as patio_id,
    nome,
    codigo,
    ferrovia,
    linha,
    uf,
    lat,
    lon,
    {{ normalizar_nome('nome') }} as nome_normalizado
from {{ source('infrasa', 'patios') }}
where nome is not null
    -- Alguns pátios vêm com coordenada NaN, que o Postgres não trata como nulo.
    and lat <> 'NaN'
    and lon <> 'NaN'
