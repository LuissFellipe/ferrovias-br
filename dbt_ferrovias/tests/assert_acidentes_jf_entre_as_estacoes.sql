-- O acidente registrado "entre A e B" tem de cair no traçado entre os pátios
-- de A e de B, com folga de 300 m (o pátio é um ponto num pátio de manobra que
-- pode ter mais de 1 km). Pega erro na interpolação, que o teste das estações
-- não vê. É um alarme para erro grosseiro: com os acidentes deslocados
-- 400 m, um sai do intervalo e o teste falha; com 150 m, passa.
select n.acidente_id, a.estacao_anterior, a.estacao_posterior, n.cadeia_m, ea.cadeia_m as cadeia_anterior, ep.cadeia_m as cadeia_posterior
from {{ ref('int_acidentes__na_linha_jf') }} n
join {{ ref('int_acidentes__deduplicados') }} a using (acidente_id)
join {{ ref('int_estacoes__km_linha_jf') }} ea on ea.estacao = a.estacao_anterior
join {{ ref('int_estacoes__km_linha_jf') }} ep on ep.estacao = a.estacao_posterior
where n.cadeia_m not between least(ea.cadeia_m, ep.cadeia_m) - 300 and greatest(ea.cadeia_m, ep.cadeia_m) + 300
