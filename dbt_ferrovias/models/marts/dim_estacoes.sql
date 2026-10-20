select
    estacao_id,
    estacao,
    uf,
    ferrovia_principal,
    lat,
    lon,
    fonte_coordenada,
    lat is not null as geolocalizada
from {{ ref('int_estacoes__geolocalizadas') }}
