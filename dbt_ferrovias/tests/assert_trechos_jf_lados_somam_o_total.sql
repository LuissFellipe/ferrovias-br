-- Esquerda mais direita tem de dar a faixa inteira. A faixa de um lado só é
-- calculada à parte e difere da inteira em até 35 pessoas por arredondamento
-- da geometria; acima de 50 pessoas e de 2% do trecho, algo está errado.
select trecho_km, pessoas_esquerda, pessoas_direita, pessoas_500m
from {{ ref('fct_trechos_jf') }}
where abs(pessoas_esquerda + pessoas_direita - pessoas_500m) > greatest(50, 0.02 * pessoas_500m)
