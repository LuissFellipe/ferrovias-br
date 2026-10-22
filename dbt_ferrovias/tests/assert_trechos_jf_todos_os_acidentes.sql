-- Todo acidente de 2011 em diante com posição no traçado tem de cair em algum
-- trecho. Um trecho que some (o meio fora do município, uma estação de
-- referência a menos) leva os acidentes junto, e o ranking não percebe.
select
    (select sum(acidentes) from {{ ref('fct_trechos_jf') }}) as nos_trechos,
    count(*) as posicionados
from {{ ref('fct_acidentes_na_linha_jf') }} n
join {{ ref('fct_acidentes') }} a using (acidente_id)
where a.registro_completo
having count(*) <> (select sum(acidentes) from {{ ref('fct_trechos_jf') }})
