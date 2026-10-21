select
    make_date(e.ano, e.mes, 1) as mes,
    e.uf_produto as uf_nome,
    u.uf,
    split_part(e.urf, ' - ', 1) as urf,
    e.sh4,
    e.kg / 1000 as toneladas
from {{ source('comex', 'comex_exportacao') }} e
left join {{ ref('ufs_comex') }} u on u.nome = e.uf_produto
