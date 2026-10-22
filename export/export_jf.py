"""Exporta a análise dos trechos de Juiz de Fora para a página juiz-de-fora.html.

O ranking (ranking_jf.py) é calculado aqui, e não no dbt, porque precisa de
uma regressão binomial negativa. O notebook 05 usa as mesmas funções, então o
número do notebook é o da página.

Nenhum dado de suicídio sai por trecho: apontar o lugar onde suicídios se
concentram é desaconselhado pelas recomendações de comunicação da OMS, e a
causa só é registrada desde dez/2020. A página fala do tema só no agregado.
"""

from datetime import datetime, timezone

import numpy as np
from scipy import stats

import ranking_jf
from db import conectar
from export_site import gravar

TOP = 5

RUAS_NO_TRECHO = """
    with l as (select geom, comprimento_m from staging.stg_osm__linha_jf),
    cruzamentos as (
        select r.tags->>'name' as nome,
               st_linelocatepoint(l.geom, (st_dump(st_intersection(st_transform(r.geom, 31983), l.geom))).geom) * l.comprimento_m as cadeia_m
        from raw.osm_jf r, l
        where r.tipo = 'way' and r.tags ? 'name' and r.tags ? 'highway'
            and coalesce(r.tags->>'bridge', 'no') = 'no' and coalesce(r.tags->>'tunnel', 'no') = 'no'
            and st_intersects(st_transform(r.geom, 31983), l.geom)
    )
    select t.trecho_km, c.nome, min(c.cadeia_m) as cadeia_m
    from intermediate.int_trechos_jf t
    join cruzamentos c on c.cadeia_m >= t.cadeia_inicio_m and c.cadeia_m < t.cadeia_fim_m
    group by 1, 2 order by 1, 3
"""

ESCOLAS_PERTO = """
    select t.trecho_km, e.nome, e.rede, round(st_distance(e.geom, t.geom)) as distancia_m
    from intermediate.int_trechos_jf t
    join staging.stg_inep__escolas_jf e on st_dwithin(e.geom, t.geom, 500)
    order by 1, 4
"""


def antes_e_depois(atropelamentos, trecho=275, inicio_depois=2022, fim_antes=2020):
    """Passarela da Estação Central, restaurada de ago/2021 a fev/2022.

    Compara o trecho com o resto de JF antes (2011–2020) e depois (2022–2025),
    deixando de fora o ano da obra. Condicional ao total do trecho, o número
    depois é binomial; a razão das chances contra o resto de JF é a razão das
    razões de taxas.
    """
    a = atropelamentos
    no_trecho = a["trecho_km"] == trecho
    antes, depois = a["ano"] <= fim_antes, a["ano"] >= inicio_depois
    x1, x0 = int((no_trecho & depois).sum()), int((no_trecho & antes).sum())
    c1, c0 = int((~no_trecho & depois).sum()), int((~no_trecho & antes).sum())
    p_controle = c1 / (c1 + c0)
    teste = stats.binomtest(x1, x1 + x0, p=p_controle)
    ic = teste.proportion_ci(0.95)
    chance = lambda p: p / (1 - p)
    return {
        "trecho_km": trecho,
        "antes": [x0, c0], "depois": [x1, c1],
        "razao": round((x1 / x0) / (c1 / c0), 2),
        "ic95": [round(float(chance(ic.low) / chance(p_controle)), 2), round(float(chance(ic.high) / chance(p_controle)), 2)],
        "p": round(float(teste.pvalue), 2),
    }


def perfil(atropelamentos, trecho):
    a = atropelamentos[atropelamentos["trecho_km"] == trecho]
    horas = [0] * 8
    for h in a["hora"].dropna():
        horas[h.hour // 3] += 1
    fim_de_semana = sum(d.weekday() >= 5 for d in a["data"])
    return {
        "horas": horas,
        "fim_de_semana": round(fim_de_semana / len(a), 2) if len(a) else None,
        "em_pn": round(a["em_pn"].mean(), 2) if len(a) else None,
        "interrupcao_h": round(float(a["interrupcao_h"].sum()), 1),
    }


def main():
    with conectar() as conn:
        trechos, atropelamentos = ranking_jf.ler(conn)
        geometrias = {k: g for k, g in conn.execute(
            "select trecho_km, st_asgeojson(st_simplify(geom, 0.00002), 5)::json->'coordinates' from marts.fct_trechos_jf")}
        pontos = conn.execute("""
            select n.lon, n.lat, a.ano, a.em_passagem_em_nivel, a.obitos > 0, n.trecho_km
            from marts.fct_acidentes_na_linha_jf n join marts.fct_acidentes a using (acidente_id)
            where a.registro_completo and a.natureza = 'Atropelamento' order by a.data_ocorrencia""").fetchall()
        ruas, escolas = {}, {}
        for k, nome, _ in conn.execute(RUAS_NO_TRECHO):
            ruas.setdefault(k, []).append(nome)
        for k, nome, rede, dist in conn.execute(ESCOLAS_PERTO):
            escolas.setdefault(k, []).append([nome, rede, int(dist)])
        ultimo = conn.execute("select max(data_ocorrencia) from marts.fct_acidentes").fetchone()[0]

    ranking, modelo = ranking_jf.ajustar(trechos)
    so_comercio, _ = ranking_jf.ajustar(trechos, exposicao=["comercio_servico_500m"])
    custo, letalidade = ranking_jf.custo_do_excesso(ranking, atropelamentos)
    robustez = ranking_jf.robustez_posicao(trechos, atropelamentos)
    t = trechos.merge(ranking.drop(columns="observado"), on="trecho_km").merge(custo.drop(columns="excesso"), on="trecho_km")
    top = t.nsmallest(TOP, "posicao")["trecho_km"].tolist()

    gravar("jf.json", {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "ultimo_dia": ultimo.isoformat(),
        "anos": ranking_jf.ANOS,
        "custo_obito_rs": round(ranking_jf.CUSTO_OBITO_RS),
        "letalidade": round(letalidade, 3),
        "modelo": {
            "coeficientes": {k: round(v, 3) for k, v in modelo.params.items()},
            "p": {k: round(v, 3) for k, v in modelo.pvalues.items()},
            "aic": round(modelo.aic, 1),
        },
        "top_so_comercio": so_comercio.nsmallest(TOP, "posicao")["trecho_km"].tolist(),
        "top_contagem": trechos.nlargest(TOP, "atropelamentos")["trecho_km"].tolist(),
        "robustez": {"sorteios": 200, "erro_m": 200, "top3": robustez},
        "antes_depois": antes_e_depois(atropelamentos),
        "trechos": [
            {
                "km": int(r.trecho_km),
                "linha": geometrias[r.trecho_km],
                "comprimento_m": round(r.comprimento_m),
                "moradores": round(r.pessoas_500m),
                "moradores_lados": [round(r.pessoas_esquerda), round(r.pessoas_direita)],
                "comercio": int(r.comercio_servico_500m),
                "escolas": int(r.escolas_500m),
                "saude": int(r.saude_500m),
                "travessias": int(r.travessias_osm),
                "atropelamentos": int(r.atropelamentos),
                "em_pn": int(r.atropelamentos_em_pn),
                "obitos": int(r.obitos_atropelamento),
                "esperado": round(r.esperado, 2),
                "eb": round(r.eb, 2),
                "eb_ic90": [round(r.eb_p05, 2), round(r.eb_p95, 2)],
                "excesso": round(r.excesso, 2),
                "p_acima": round(r.p_acima_do_esperado, 2),
                "posicao": int(r.posicao),
                "obitos_evitaveis_ano": round(r.obitos_evitaveis_por_ano, 3),
                "valor_social_ano_rs": round(r.valor_social_por_ano_rs, -3),
                "ruas": ruas.get(r.trecho_km, []),
                "escolas_perto": escolas.get(r.trecho_km, [])[:3],
                **({"perfil": perfil(atropelamentos, r.trecho_km)} if r.trecho_km in top else {}),
            }
            for r in t.itertuples()
        ],
        # [lon·1e5, lat·1e5, ano, em passagem em nível, com óbito, trecho]
        "atropelamentos": [
            [round(lon * 1e5), round(lat * 1e5), ano, int(pn), int(obito), trecho]
            for lon, lat, ano, pn, obito, trecho in pontos
        ],
    })
    print(f"top {TOP}: {top}; robustez {robustez}")


if __name__ == "__main__":
    np.seterr(all="ignore")
    main()
