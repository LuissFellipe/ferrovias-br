select
    mercadoria_antt,
    grupo,
    perigosa,
    grupo = 'Minério de ferro' as minerio_de_ferro,
    -- Quatro categorias para colorir o mapa: mais cores que isso deixam de
    -- ser distinguíveis quando os arcos se cruzam.
    case
        when grupo = 'Minério de ferro' then 'Minério de ferro'
        when grupo in ('Siderurgia', 'Carvão e coque') then 'Siderurgia e carvão'
        when grupo in ('Grãos e farelos', 'Açúcar', 'Celulose e madeira', 'Fertilizantes') then 'Agronegócio'
        else 'Outras cargas'
    end as categoria
from {{ ref('mercadorias') }}
