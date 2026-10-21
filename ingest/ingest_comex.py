"""Carrega as exportações mensais por UF do produto, porto e mercadoria (Comex Stat).

O lado do trilho já está no SIADE: o que chega de trem às estações de um
porto. Para saber quanto chega por outro meio, falta o total exportado pelo
mesmo porto, e o Comex Stat tem isso por URF (a unidade da Receita que
despacha a carga, que no caso do porto é o próprio porto).

Os arquivos em lote do Comex Stat ficam num servidor com o certificado
vencido desde 03/10/2026. A API (api-comexstat.mdic.gov.br) tem certificado
válido e devolve o mesmo dado agregado, então a carga usa a API e não
desliga a verificação de TLS.

A API limita a frequência de consultas, e o limite pesa mais nos servidores
compartilhados do GitHub Actions: em 21/10/2026 ela recusou 8 tentativas
seguidas para 2018, enquanto respondia normalmente de outra máquina. Por isso
o repositório guarda uma cópia em ingest/comex_exportacao_*.csv.gz. Os anos
fechados (até dois anos atrás, que não recebem mais revisão) vêm sempre da
cópia; os dois mais recentes vêm da API e só caem na cópia, com aviso, se a
API recusar. Para renovar a cópia, rode com --gravar-copia.
"""

import csv
import gzip
import sys
import time
from datetime import date
from pathlib import Path

import requests

from db import conectar

API = "https://api-comexstat.mdic.gov.br/general"
ANO_INICIAL = 2015
# A mesma tabela que o dbt usa para casar a posição SH4 com a mercadoria do
# SIADE: uma posição nova entra lá e passa a ser baixada aqui.
PRODUTOS = Path(__file__).resolve().parent.parent / "dbt_ferrovias" / "seeds" / "produtos_exportacao.csv"
# Consultas seguidas param no limite da API, que segue respondendo 429 por
# bem mais que os 10 s que a mensagem dela pede.
PAUSA = 15
PASTA = Path(__file__).resolve().parent

DDL = """
create schema if not exists raw;
create table if not exists raw.comex_exportacao (
    ano int not null,
    mes int not null,
    uf_produto text not null,
    urf text not null,
    sh4 text not null,
    kg numeric not null,
    carregado_em timestamptz not null default now(),
    primary key (ano, mes, uf_produto, urf, sh4)
);
"""


def consultar(corpo, tentativas=8):
    # A API limita a frequência de consultas: acima dela responde 429 e pede
    # para esperar alguns segundos.
    for tentativa in range(1, tentativas + 1):
        try:
            resp = requests.post(API, json=corpo, timeout=180)
            if resp.status_code == 429:
                raise requests.RequestException("429, limite de consultas")
            resp.raise_for_status()
            dados = resp.json()
            if not dados.get("success", True) or "data" not in dados:
                raise requests.RequestException(f"resposta sem dados: {str(dados)[:200]}")
            return dados["data"]["list"]
        except requests.RequestException as erro:
            if tentativa == tentativas:
                raise
            espera = 12 * tentativa
            print(f"falha no Comex Stat ({erro}), nova tentativa em {espera}s")
            time.sleep(espera)


def exportacoes(ano, posicoes):
    ultimo_mes = 12 if ano < date.today().year else date.today().month
    linhas = consultar({
        "flow": "export",
        "monthDetail": True,
        "period": {"from": f"{ano}-01", "to": f"{ano}-{ultimo_mes:02d}"},
        "filters": [{"filter": "heading", "values": posicoes}],
        "details": ["state", "urf", "heading"],
        "metrics": ["metricKG"],
    })
    for r in linhas:
        yield (
            int(r["year"]), int(r["monthNumber"]), r["state"], r["urf"],
            r["headingCode"], r["metricKG"],
        )


def ler_copia():
    copias = sorted(PASTA.glob("comex_exportacao_*.csv.gz"))
    if not copias:
        return {}, None
    por_ano = {}
    with gzip.open(copias[-1], "rt", newline="", encoding="utf-8") as arq:
        for r in csv.DictReader(arq):
            por_ano.setdefault(int(r["ano"]), []).append(
                (int(r["ano"]), int(r["mes"]), r["uf_produto"], r["urf"], r["sh4"], r["kg"])
            )
    return por_ano, copias[-1].name


def gravar_copia(conn):
    destino = PASTA / f"comex_exportacao_{date.today().isoformat()}.csv.gz"
    with gzip.open(destino, "wt", newline="", encoding="utf-8") as arq:
        escritor = csv.writer(arq)
        escritor.writerow(["ano", "mes", "uf_produto", "urf", "sh4", "kg"])
        escritor.writerows(conn.execute(
            "select ano, mes, uf_produto, urf, sh4, kg from raw.comex_exportacao order by 1, 2, 3, 4, 5"
        ))
    print(f"cópia gravada em {destino.name}")


def main():
    gravar = "--gravar-copia" in sys.argv
    with open(PRODUTOS, encoding="utf-8") as f:
        posicoes = sorted({r["sh4"] for r in csv.DictReader(f)})
    copia, nome_copia = ({}, None) if gravar else ler_copia()
    with conectar() as conn:
        conn.autocommit = True
        conn.execute(DDL)
        carregados = {
            r[0] for r in conn.execute("select distinct ano from raw.comex_exportacao").fetchall()
        }
        hoje = date.today()
        for ano in range(ANO_INICIAL, hoje.year + 1):
            # O ano corrente e o anterior ainda recebem revisões; os demais
            # são carregados uma vez.
            fechado = ano < hoje.year - 1
            if ano in carregados and fechado and not gravar:
                continue
            if fechado and ano in copia:
                linhas, origem = copia[ano], f"cópia {nome_copia}"
            else:
                try:
                    linhas, origem = list(exportacoes(ano, posicoes)), "API"
                except requests.RequestException as erro:
                    if gravar or ano not in copia:
                        raise
                    linhas, origem = copia[ano], f"cópia {nome_copia}"
                    print(f"AVISO: Comex Stat recusou {ano} ({erro}); usando a {origem}")
                time.sleep(PAUSA)
            with conn.transaction():
                conn.execute("delete from raw.comex_exportacao where ano = %s", (ano,))
                with conn.cursor().copy(
                    "copy raw.comex_exportacao (ano, mes, uf_produto, urf, sh4, kg) from stdin"
                ) as copy:
                    for linha in linhas:
                        copy.write_row(linha)
            print(f"comex {ano}: {len(linhas)} linhas ({origem})")
        if gravar:
            gravar_copia(conn)


if __name__ == "__main__":
    main()
