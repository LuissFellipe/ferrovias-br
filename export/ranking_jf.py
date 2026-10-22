"""Ranking dos trechos de Juiz de Fora pelo excesso de atropelamentos.

A contagem bruta põe no topo o trecho mais movimentado, e não o mais perigoso.
O ranking compara cada trecho com o que se esperaria de um trecho com a mesma
exposição, pelo método empírico-bayesiano do Highway Safety Manual (Hauer):

1. Uma regressão binomial negativa, ajustada em todos os trechos, diz quantos
   atropelamentos se esperam de um trecho com aquela exposição: comércio e
   serviço e moradores a até 500 m, com o comprimento do trecho como offset.
2. O número empírico-bayesiano mistura o esperado com o observado. O peso do
   observado cresce com o número esperado: um trecho de pouco movimento com 3
   atropelamentos num ano ruim volta para perto da média (regressão à média),
   e um trecho movimentado é julgado mais pelo próprio histórico.
3. O excesso é o empírico-bayesiano menos o esperado. É o que uma intervenção
   tem a ganhar no trecho, em atropelamentos em 15 anos.

O comércio entra porque o Censo conta quem mora, e o centro é comercial. Em
22/10/2026, com as duas exposições, o coeficiente do comércio foi 0,43
(p = 0,01) e o dos moradores 0,16 (p = 0,37). Só com moradores, a binomial
negativa não acha sobredispersão e a Poisson tem AIC 197, contra 165.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

ANOS = 15  # 2011 a 2025, a série comparável do RAAF
EXPOSICAO = ["comercio_servico_500m", "pessoas_500m"]
# Custo social médio de um acidente com morte nas rodovias federais em 2014
# (Ipea e PRF, 2015: R$ 646,7 mil), corrigido pelo IPCA de jan/2015 a dez/2025
# (fator 1,8235, série 433 do SGS do Banco Central). É ordem de grandeza: a
# conta foi feita para acidente rodoviário, não para atropelamento por trem.
CUSTO_OBITO_RS = 646_700 * 1.8235

CONSULTA_TRECHOS = """
    select trecho_km, comprimento_m, pessoas_500m, pessoas_esquerda, pessoas_direita,
           comercio_servico_500m, escolas_500m, saude_500m, travessias_osm,
           acidentes, atropelamentos, atropelamentos_em_pn, obitos_atropelamento
    from marts.fct_trechos_jf order by trecho_km
"""

CONSULTA_ATROPELAMENTOS = """
    select n.km::float as km, n.trecho_km, a.ano, a.data_ocorrencia as data, a.hora_ocorrencia as hora,
           a.em_passagem_em_nivel as em_pn, a.obitos, coalesce(a.interrupcao_h, 0)::float as interrupcao_h
    from marts.fct_acidentes_na_linha_jf n
    join marts.fct_acidentes a using (acidente_id)
    where a.registro_completo and a.natureza = 'Atropelamento'
"""


def consultar(conn, sql):
    cur = conn.execute(sql)
    return pd.DataFrame(cur.fetchall(), columns=[c.name for c in cur.description])


def ler(conn):
    trechos = consultar(conn, CONSULTA_TRECHOS)
    atropelamentos = consultar(conn, CONSULTA_ATROPELAMENTOS)
    num = trechos.columns.drop("trecho_km")
    trechos[num] = trechos[num].astype(float)
    return trechos, atropelamentos


def ajustar(trechos, contagem="atropelamentos", exposicao=EXPOSICAO):
    """Binomial negativa + empírico-bayesiano. Devolve (tabela, modelo)."""
    X = sm.add_constant(np.log1p(trechos[exposicao]))
    offset = np.log(trechos["comprimento_m"] / 1000)
    modelo = sm.NegativeBinomial(trechos[contagem], X, offset=offset).fit(disp=0, maxiter=500)
    if not modelo.mle_retvals["converged"]:
        raise RuntimeError("a binomial negativa não convergiu")
    alfa = modelo.params["alpha"]
    if alfa <= 1e-6:
        # Sem sobredispersão o peso do observado iria a zero e todo trecho
        # ficaria igual ao esperado: a conta perde o sentido.
        raise RuntimeError("binomial negativa sem sobredispersão (alfa ~ 0)")
    esperado = np.exp(X @ modelo.params.drop("alpha") + offset)
    peso = 1 / (1 + alfa * esperado)
    observado = trechos[contagem]
    # A posteriori do número de atropelamentos é uma gama: forma 1/alfa + y,
    # taxa 1/(alfa·esperado) + 1. A média dela é o empírico-bayesiano.
    forma, taxa = 1 / alfa + observado, 1 / (alfa * esperado) + 1
    t = trechos[["trecho_km"]].copy()
    t["observado"] = observado
    t["esperado"] = esperado
    t["eb"] = peso * esperado + (1 - peso) * observado
    t["eb_p05"] = stats.gamma.ppf(0.05, forma, scale=1 / taxa)
    t["eb_p95"] = stats.gamma.ppf(0.95, forma, scale=1 / taxa)
    t["excesso"] = t["eb"] - esperado
    t["p_acima_do_esperado"] = 1 - stats.gamma.cdf(esperado, forma, scale=1 / taxa)
    t["posicao"] = t["excesso"].rank(ascending=False, method="first").astype(int)
    return t, modelo


def robustez_posicao(trechos, atropelamentos, erro_km=0.2, sorteios=200, top=3, semente=3):
    """Quantas vezes cada trecho fica no top N com o km perturbado em ±erro."""
    rng = np.random.default_rng(semente)
    contagem = {}
    for _ in range(sorteios):
        km = np.floor(atropelamentos["km"] + rng.normal(0, erro_km, len(atropelamentos))).astype(int)
        t = trechos.copy()
        t["atropelamentos"] = t["trecho_km"].map(pd.Series(km).value_counts()).fillna(0)
        r, _ = ajustar(t)
        for k in r.nsmallest(top, "posicao")["trecho_km"]:
            contagem[int(k)] = contagem.get(int(k), 0) + 1
    return contagem


def custo_do_excesso(ranking, atropelamentos):
    """Óbitos e valor social por ano que o excesso de cada trecho representa.

    A letalidade é a de JF inteira (óbitos por atropelamento), e não a de cada
    trecho: com 5 a 30 atropelamentos por trecho, a fração de cada um oscila
    demais.
    """
    letalidade = atropelamentos["obitos"].sum() / len(atropelamentos)
    c = ranking[["trecho_km", "excesso"]].copy()
    c["excesso_por_ano"] = c["excesso"].clip(lower=0) / ANOS
    c["obitos_evitaveis_por_ano"] = c["excesso_por_ano"] * letalidade
    c["valor_social_por_ano_rs"] = c["obitos_evitaveis_por_ano"] * CUSTO_OBITO_RS
    return c, letalidade
