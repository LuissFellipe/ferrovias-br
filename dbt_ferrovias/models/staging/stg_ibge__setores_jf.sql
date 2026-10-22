select
    cd_setor,
    situacao,
    pessoas,
    st_transform(geom, 31983) as geom,
    st_area(st_transform(geom, 31983)) as area_m2
from {{ source('exposicao', 'setores_jf') }}
