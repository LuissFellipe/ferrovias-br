-- Acidentes da MRS em Juiz de Fora com a posição no traçado, e não no pátio
-- da estação. É o que a análise por trecho usa.
--
-- O trecho é de 1 km do km oficial, e não de 500 m. Com um erro de posição de
-- ±200 m, 34% dos atropelamentos trocariam de trecho de 500 m, e o ranking dos
-- trechos muda quando a grade é deslocada em 250 m. Com 1 km, 19% trocam, e
-- em 200 sorteios os km 275 e 274 ficam no top 3 em 200 e 198, o 273 em 162.
select
    a.acidente_id,
    a.km_inicial as km,
    floor(a.km_inicial)::int as trecho_km,
    n.cadeia_m,
    n.vao_entre_ancoras_km,
    st_y(n.geom) as lat,
    st_x(n.geom) as lon
from {{ ref('int_acidentes__na_linha_jf') }} n
join {{ ref('int_acidentes__deduplicados') }} a using (acidente_id)
where a.municipio ilike 'juiz de fora%'
