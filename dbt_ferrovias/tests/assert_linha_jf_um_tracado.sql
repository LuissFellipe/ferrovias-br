-- A posição do acidente é medida ao longo da linha principal. Se uma edição no
-- OSM partir o traçado em dois, a medida perde o sentido.
select count(*) as tracados
from {{ ref('stg_osm__linha_jf') }}
having count(*) <> 1
