"""Carrega os pátios ferroviários declarados pelas concessionárias à ANTT.

O SIADE identifica cada estação só pelo nome e pela UF. As coordenadas vêm da
camada de pátios da InfraSA (antiga EPL), um serviço ArcGIS que devolve no
máximo 2.000 registros por consulta. A camada é pequena, então é recarregada
inteira a cada execução.

Em 21/10/2026 o domínio infrasa.gov.br inteiro parou de resolver (SERVFAIL no
Google e na Cloudflare), e o GitHub Actions caiu antes de chegar à ANTT. Por
isso o repositório guarda uma cópia da camada em ingest/patios_infrasa_*.csv:
quando a InfraSA não responde, a carga usa a cópia mais recente e avisa. Para
renovar a cópia com a camada do dia, rode com --gravar-copia.
"""

import csv
import sys
import time
from datetime import date
from pathlib import Path

import requests

from db import conectar

SERVICO = (
    "https://geo.infrasa.gov.br/server/rest/services/"
    "P%C3%A1tio_Ferrovi%C3%A1rio/MapServer/0/query"
)
POR_PAGINA = 2000
PASTA = Path(__file__).resolve().parent
COLUNAS = ["objectid", "nome", "codigo", "ferrovia", "linha", "uf", "lon", "lat"]

DDL = """
create schema if not exists raw;
create table if not exists raw.patios (
    objectid int primary key,
    nome text,
    codigo text,
    ferrovia text,
    linha text,
    uf text,
    lon double precision not null,
    lat double precision not null,
    carregado_em timestamptz not null default now()
);
"""


def pagina(deslocamento, tentativas=5):
    params = {
        "where": "1=1",
        "outFields": "objectid,nomeestaca,codigotres,vhr_ferrov,vhr_nomeli,uf",
        "outSR": 4326,
        "resultOffset": deslocamento,
        "resultRecordCount": POR_PAGINA,
        "orderByFields": "objectid",
        "f": "json",
    }
    for tentativa in range(1, tentativas + 1):
        try:
            resp = requests.get(SERVICO, params=params, timeout=120)
            resp.raise_for_status()
            dados = resp.json()
            # O ArcGIS responde 200 com {"error": ...} quando a consulta falha.
            if "error" in dados:
                raise requests.RequestException(dados["error"])
            return dados
        except requests.RequestException as erro:
            if tentativa == tentativas:
                raise
            espera = 2 ** tentativa
            print(f"falha na InfraSA ({erro}), nova tentativa em {espera}s")
            time.sleep(espera)


def baixar():
    feicoes, deslocamento = [], 0
    while True:
        dados = pagina(deslocamento)
        feicoes += dados["features"]
        if not dados.get("exceededTransferLimit"):
            return feicoes
        deslocamento += POR_PAGINA


def da_infrasa():
    linhas = []
    for f in baixar():
        a, g = f["attributes"], f["geometry"]
        linhas.append((
            a["objectid"], a["nomeestaca"], a["codigotres"], a["vhr_ferrov"],
            a["vhr_nomeli"], a["uf"], g["x"], g["y"],
        ))
    return linhas


def da_copia():
    copias = sorted(PASTA.glob("patios_infrasa_*.csv"))
    if not copias:
        raise RuntimeError("a InfraSA não respondeu e não há cópia dos pátios no repositório")
    with copias[-1].open(newline="", encoding="utf-8") as arq:
        leitor = csv.DictReader(arq)
        # Vazio no CSV é nulo; a coordenada NaN da camada volta como NaN, que o
        # staging já descarta.
        linhas = [
            tuple(None if r[c] == "" else r[c] for c in COLUNAS[:6]) + (float(r["lon"]), float(r["lat"]))
            for r in leitor
        ]
    return linhas, copias[-1].name


def gravar_copia(linhas):
    destino = PASTA / f"patios_infrasa_{date.today().isoformat()}.csv"
    with destino.open("w", newline="", encoding="utf-8") as arq:
        escritor = csv.writer(arq)
        escritor.writerow(COLUNAS)
        escritor.writerows(("" if v is None else v for v in linha) for linha in sorted(linhas))
    print(f"cópia gravada em {destino.name}")


def main():
    try:
        linhas = da_infrasa()
        origem = "InfraSA"
    except requests.RequestException as erro:
        linhas, nome = da_copia()
        origem = f"cópia {nome}"
        print(f"AVISO: InfraSA fora do ar ({erro.__class__.__name__}); usando a {origem}")
    if "--gravar-copia" in sys.argv:
        if origem != "InfraSA":
            raise RuntimeError("a cópia só pode ser renovada com a camada baixada da InfraSA")
        gravar_copia(linhas)
    with conectar() as conn:
        conn.execute(DDL)
        conn.execute("truncate raw.patios")
        with conn.cursor().copy(f"copy raw.patios ({', '.join(COLUNAS)}) from stdin") as copy:
            for linha in linhas:
                copy.write_row(linha)
        conn.commit()
    print(f"{len(linhas)} pátios ({origem})")


if __name__ == "__main__":
    main()
