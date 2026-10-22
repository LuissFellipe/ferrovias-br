-- Quase todo acidente da MRS em Juiz de Fora na Linha do Centro tem de ganhar
-- posição no traçado. Em 22/10/2026 ficaram de fora 4 de 256: um sem km e três
-- com km de outro município (219,8, 238 e 322,5). Falha abaixo de 98%.
select count(n.acidente_id)::numeric / count(*) as fracao
from {{ ref('int_acidentes__deduplicados') }} a
left join {{ ref('int_acidentes__na_linha_jf') }} n using (acidente_id)
where a.ferrovia = 'MRS'
    and a.linha_ferrea = 'Posto km 64 - 452 (Linha do Centro)'
    and a.municipio ilike 'juiz de fora%'
having count(n.acidente_id)::numeric / count(*) < 0.98
