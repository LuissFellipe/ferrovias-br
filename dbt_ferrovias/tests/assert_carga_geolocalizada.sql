-- Para o mapa, toda estação da MRS precisa de coordenada; nas outras ferrovias
-- basta que quase toda a carga tenha. Uma estação nova da MRS sem pátio
-- correspondente para o pipeline até entrar em seeds/estacoes_manuais.csv.
with pontas as (
    select f.ferrovia, f.tu, o.geolocalizada and d.geolocalizada as geolocalizada
    from {{ ref('fct_producao_mensal') }} f
    join {{ ref('dim_estacoes') }} o on o.estacao_id = f.origem_id
    join {{ ref('dim_estacoes') }} d on d.estacao_id = f.destino_id
)

select 'MRS' as recorte, sum(tu) filter (where not geolocalizada) as tu_sem_coordenada
from pontas
where ferrovia = 'MRS'
having sum(tu) filter (where not geolocalizada) > 0

union all

select 'todas', sum(tu) filter (where not geolocalizada)
from pontas
having sum(tu) filter (where not geolocalizada) > 0.005 * sum(tu)
