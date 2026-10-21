"""Exporta os acidentes para a página de segurança do painel.

Mesmo princípio do export_site: o navegador recebe todos os acidentes desde
2004 (cerca de 14,5 mil) e filtra sozinho. Cada acidente vira uma lista de
inteiros que apontam para as listas de seguranca_meta.json, e o ponto do mapa
é o pátio da estação, então acidentes do mesmo pátio dividem o mesmo índice
de local.
"""

from datetime import datetime, timezone

from db import conectar
from export_site import gravar

NATUREZAS = ["Atropelamento", "Abalroamento", "Descarrilamento", "Outras"]


def main():
    with conectar() as conn:
        q = lambda sql: conn.execute(sql).fetchall()
        ferrovias = q("""
            select f.ferrovia, f.nome from marts.dim_ferrovias f
            where exists (select 1 from marts.fct_acidentes a where a.ferrovia = f.ferrovia)
            order by f.ferrovia""")
        locais = q("""
            select coalesce(estacao_anterior, estacao_posterior), lat, lon
            from marts.fct_acidentes where lat is not null
            group by 1, 2, 3 order by 1, 2, 3""")
        municipios = q("""
            select municipio, uf from marts.fct_acidentes where municipio is not null
            group by 1, 2 order by 1, 2""")
        acidentes = q("""
            select ano, ferrovia, natureza, grave, obitos, feridos, em_passagem_em_nivel,
                   coalesce(estacao_anterior, estacao_posterior), lat, lon, municipio, uf,
                   (causa_contributiva ilike '%%suic%%')
            from marts.fct_acidentes order by data_ocorrencia, acidente_id""")
        anual = q("""
            select ferrovia, ano, acidentes, graves, obitos, tku, indice_oficial
            from marts.fct_acidentes_ferrovia_anual order by 1, 2""")
        ultimo = conn.execute("select max(data_ocorrencia) from marts.fct_acidentes").fetchone()[0]

    i_fer = {f[0]: i for i, f in enumerate(ferrovias)}
    i_loc = {l: i for i, l in enumerate(locais)}
    i_mun = {m: i for i, m in enumerate(municipios)}
    natureza = lambda n: NATUREZAS.index(n) if n in NATUREZAS else NATUREZAS.index("Outras")
    coord = lambda v: round(v * 1e4)

    gravar("seguranca_meta.json", {
        "ultimo_dia": ultimo.isoformat(),
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "naturezas": NATUREZAS,
        "ferrovias": [list(f) for f in ferrovias],
        "locais": [[nome, coord(lat), coord(lon)] for nome, lat, lon in locais],
        "municipios": [list(m) for m in municipios],
        # TKU em milhões para caber em inteiro; o índice oficial com 2 casas.
        "anual": [
            [i_fer[f], ano, acid, graves, obitos, None if tku is None else round(tku / 1000000),
             None if ind is None else round(float(ind), 2)]
            for f, ano, acid, graves, obitos, tku, ind in anual if f in i_fer
        ],
    })
    gravar("acidentes.json", [
        [ano, i_fer[f], natureza(nat), int(grave), obitos, feridos, int(pn),
         -1 if lat is None else i_loc[(est, lat, lon)],
         -1 if mun is None else i_mun[(mun, uf)], int(bool(suic))]
        for ano, f, nat, grave, obitos, feridos, pn, est, lat, lon, mun, uf, suic in acidentes
    ])


if __name__ == "__main__":
    main()
