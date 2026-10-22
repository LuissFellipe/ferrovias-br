select
    code_school as escola_id,
    name_school as nome,
    admin_category as rede,
    education_level as etapas,
    st_transform(geom, 31983) as geom
from {{ source('exposicao', 'escolas_jf') }}
