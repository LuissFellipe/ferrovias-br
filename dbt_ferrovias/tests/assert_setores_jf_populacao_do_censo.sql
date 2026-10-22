-- O recorte dos setores tem de somar a população oficial de Juiz de Fora no
-- Censo 2022. Um recorte parcial (setor sem geometria, filtro errado) muda a
-- exposição de todos os trechos sem nenhum outro aviso.
select sum(pessoas) as pessoas
from {{ ref('stg_ibge__setores_jf') }}
having sum(pessoas) <> 540756
