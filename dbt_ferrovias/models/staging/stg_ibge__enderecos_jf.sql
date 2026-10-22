select
    endereco_id,
    especie,
    st_transform(geom, 31983) as geom
from {{ source('exposicao', 'enderecos_jf') }}
