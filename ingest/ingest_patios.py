"""Carrega os pátios ferroviários declarados pelas concessionárias à ANTT.

O SIADE identifica cada estação só pelo nome e pela UF. As coordenadas vêm da
camada de pátios da InfraSA (antiga EPL), um serviço ArcGIS que devolve no
máximo 2.000 registros por consulta. A camada é pequena, então é recarregada
inteira a cada execução.
"""

import time

import requests

from db import conectar

SERVICO = (
    "https://geo.infrasa.gov.br/server/rest/services/"
    "P%C3%A1tio_Ferrovi%C3%A1rio/MapServer/0/query"
)
POR_PAGINA = 2000

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


def main():
    feicoes = baixar()
    with conectar() as conn:
        conn.execute(DDL)
        conn.execute("truncate raw.patios")
        with conn.cursor().copy(
            "copy raw.patios (objectid, nome, codigo, ferrovia, linha, uf, lon, lat) from stdin"
        ) as copy:
            for f in feicoes:
                a, g = f["attributes"], f["geometry"]
                copy.write_row((
                    a["objectid"], a["nomeestaca"], a["codigotres"], a["vhr_ferrov"],
                    a["vhr_nomeli"], a["uf"], g["x"], g["y"],
                ))
        conn.commit()
    print(f"{len(feicoes)} pátios")


if __name__ == "__main__":
    main()
