"""Exporta os marts para os JSON estáticos que o painel lê.

O painel não tem servidor: o navegador recebe os fluxos anuais e a série
mensal inteiros (cerca de 1,5 MB) e filtra por ferrovia, ano, grupo e
estação sozinho. Para caber nisso, os textos viram índices em listas do
meta.json e as coordenadas viram inteiros em décimos de milésimo de grau.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from db import conectar

SAIDA = Path(__file__).resolve().parent.parent / "site" / "data"
CATEGORIAS = ["Minério de ferro", "Siderurgia e carvão", "Agronegócio", "Outras cargas"]


def gravar(nome, dados):
    caminho = SAIDA / nome
    caminho.write_text(json.dumps(dados, ensure_ascii=False, separators=(",", ":")))
    print(f"{nome}: {caminho.stat().st_size / 1024:.0f} KB")


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    with conectar() as conn:
        q = lambda sql: conn.execute(sql).fetchall()

        ferrovias = q("""
            select f.ferrovia, f.nome, f.grupo_economico
            from marts.dim_ferrovias f
            where exists (select 1 from marts.fct_fluxos_anuais x where x.ferrovia = f.ferrovia)
            order by f.ferrovia""")
        grupos = q("""
            select grupo, min(categoria)
            from marts.dim_mercadorias group by grupo
            order by grupo = 'Outros', grupo""")
        mercadorias = q("select mercadoria_antt, grupo from marts.dim_mercadorias order by 1")
        estacoes = q("""
            select estacao_id, estacao, uf, ferrovia_principal, lat, lon
            from marts.dim_estacoes order by estacao, uf""")

        i_fer = {f[0]: i for i, f in enumerate(ferrovias)}
        i_gru = {g[0]: i for i, g in enumerate(grupos)}
        i_mer = {m[0]: i for i, m in enumerate(mercadorias)}
        i_est = {e[0]: i for i, e in enumerate(estacoes)}

        fluxos = q("""
            select ano, ferrovia, mercadoria_antt, origem_id, destino_id, tu, tku, meses
            from marts.fct_fluxos_anuais where tu > 0
            order by ano, tu desc""")
        serie = q("""
            select to_char(mes, 'YYYYMM')::int, ferrovia, grupo, tu, tku
            from marts.fct_ferrovia_grupo_mensal order by 1, 2, 3""")
        ultimo = conn.execute("select max(mes) from marts.fct_producao_mensal").fetchone()[0]

    coord = lambda v: None if v is None else round(v * 1e4)
    gravar("meta.json", {
        "ultimo_mes": ultimo.strftime("%Y-%m"),
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "categorias": CATEGORIAS,
        "ferrovias": [list(f) for f in ferrovias],
        "grupos": [[g, CATEGORIAS.index(c)] for g, c in grupos],
        "mercadorias": [[m, i_gru[g]] for m, g in mercadorias],
    })
    gravar("estacoes.json", [
        [nome, uf, i_fer.get(fer, -1), coord(lat), coord(lon)]
        for _, nome, uf, fer, lat, lon in estacoes
    ])
    gravar("fluxos.json", [
        [ano, i_fer[f], i_mer[m], i_est[o], i_est[d], tu, tku, meses]
        for ano, f, m, o, d, tu, tku, meses in fluxos
    ])
    gravar("serie.json", [[mes, i_fer[f], i_gru[g], tu, tku] for mes, f, g, tu, tku in serie])


if __name__ == "__main__":
    main()
