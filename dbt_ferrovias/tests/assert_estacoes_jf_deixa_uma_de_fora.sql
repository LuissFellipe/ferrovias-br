-- Quanto a interpolação erra: cada estação é tirada da lista e a posição dela é
-- prevista pelas vizinhas. Em 22/10/2026 o erro foi de 30 m em Juiz de Fora e
-- 16 m em Mariano Procópio, as duas com vizinhas a menos de 7 km. Com vizinhas
-- a 9–12 km, ele chega a 200–900 m, e com 24 km (Benfica), a 1,2 km. O teste
-- vigia o centro, onde estão os atropelamentos: falha acima de 150 m.
with e as (
    select
        estacao, km, cadeia_m,
        lag(km) over w as km_a, lag(cadeia_m) over w as c_a,
        lead(km) over w as km_b, lead(cadeia_m) over w as c_b
    from {{ ref('int_estacoes__km_linha_jf') }}
    window w as (order by km)
)

select estacao, c_a + (km - km_a) * (c_b - c_a) / (km_b - km_a) - cadeia_m as erro_m
from e
where km_b - km_a < 7
    and abs(c_a + (km - km_a) * (c_b - c_a) / (km_b - km_a) - cadeia_m) > 150
