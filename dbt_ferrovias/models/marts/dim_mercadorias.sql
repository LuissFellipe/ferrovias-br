select
    mercadoria_antt,
    grupo,
    perigosa,
    grupo = 'Minério de ferro' as minerio_de_ferro
from {{ ref('mercadorias') }}
