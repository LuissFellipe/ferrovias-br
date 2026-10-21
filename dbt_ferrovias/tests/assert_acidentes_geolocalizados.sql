-- Todo acidente da MRS que informa a estação tem de estar no mapa. Nas demais
-- ferrovias, ao menos 97%.
select ferrovia = 'MRS' as mrs, count(*) as acidentes, count(lat) as no_mapa
from {{ ref('fct_acidentes') }}
where estacao_anterior is not null or estacao_posterior is not null
group by 1
having count(lat) < case when bool_and(ferrovia = 'MRS') then count(*) else 0.97 * count(*) end
