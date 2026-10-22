"""Carrega do OpenStreetMap o traçado da Linha do Centro em Juiz de Fora.

O acidente da ANTT não tem coordenada: tem o quilômetro na linha. Para pôr esse
quilômetro no mapa é preciso o desenho da linha, e o da InfraSA é simplificado
demais para isso. O OSM tem a linha principal da MRS inteira entre Matias
Barbosa e Ewbank da Câmara, num traçado contínuo de 49 km, e também as ruas e
caminhos que a cruzam em nível.

A carga usa uma cópia fixa em ingest/osm_jf_*.json.gz, e não a API, por dois
motivos. O primeiro é que o km de cada acidente é posto no mapa medindo
distâncias sobre esse traçado: uma edição no OSM mudaria a posição dos
acidentes sem nenhuma mudança na ANTT. O segundo é que o Overpass recusou ou
deixou pendurada a consulta em duas de três tentativas em 22/10/2026. Para
renovar a cópia, rode com --baixar.

Dados do OSM © colaboradores do OpenStreetMap, licença ODbL.
"""

import gzip
import json
import sys
import time
from datetime import date
from pathlib import Path

import requests

from db import conectar

OVERPASS = "https://overpass-api.de/api/interpreter"
# Sul de Matias Barbosa ao norte de Ewbank da Câmara: cobre o município de Juiz
# de Fora inteiro com folga nas duas pontas.
BBOX = "-21.84,-43.53,-21.57,-43.26"
CONSULTA = f"""[out:json][timeout:120];
way["railway"="rail"]["usage"="main"]({BBOX})->.principal;
(
  .principal;
  way(around.principal:3)["highway"];
  node["railway"~"^(level_crossing|crossing)$"]({BBOX});
);
out geom tags;"""
PASTA = Path(__file__).resolve().parent

DDL = """
create schema if not exists raw;
create table if not exists raw.osm_jf (
    tipo text not null,
    osm_id bigint not null,
    tags jsonb not null,
    geom geometry(Geometry, 4326) not null,
    primary key (tipo, osm_id)
);
create table if not exists raw.osm_jf_copia (
    arquivo text not null,
    carregado_em timestamptz not null default now()
);
"""


def consultar(tentativas=5):
    for tentativa in range(1, tentativas + 1):
        try:
            resp = requests.post(
                OVERPASS,
                data={"data": CONSULTA},
                # Sem um User-Agent que identifique o projeto, o Overpass responde 406.
                headers={"User-Agent": "ferrovias-br/1.0 (github.com/LuissFellipe/ferrovias-br)"},
                timeout=180,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as erro:
            if tentativa == tentativas:
                raise
            espera = 10 * tentativa
            print(f"falha no Overpass ({erro}), nova tentativa em {espera}s")
            time.sleep(espera)


def baixar():
    dados = consultar()
    destino = PASTA / f"osm_jf_{date.today().isoformat()}.json.gz"
    with gzip.open(destino, "wt", encoding="utf-8") as arq:
        json.dump(dados, arq, ensure_ascii=False, sort_keys=True)
    print(f"cópia gravada em {destino.name}")


def wkt(elemento):
    if elemento["type"] == "node":
        return f"POINT({elemento['lon']} {elemento['lat']})"
    return "LINESTRING(" + ",".join(f"{p['lon']} {p['lat']}" for p in elemento["geometry"]) + ")"


def main():
    if "--baixar" in sys.argv:
        baixar()
    copias = sorted(PASTA.glob("osm_jf_*.json.gz"))
    if not copias:
        raise RuntimeError("não há cópia do OSM no repositório; rode com --baixar")
    with gzip.open(copias[-1], "rt", encoding="utf-8") as arq:
        elementos = json.load(arq)["elements"]
    with conectar() as conn:
        conn.execute(DDL)
        conn.execute("truncate raw.osm_jf, raw.osm_jf_copia")
        with conn.cursor() as cur:
            cur.executemany(
                "insert into raw.osm_jf values (%s, %s, %s, st_geomfromtext(%s, 4326))",
                [(e["type"], e["id"], json.dumps(e.get("tags", {}), ensure_ascii=False), wkt(e)) for e in elementos],
            )
        conn.execute("insert into raw.osm_jf_copia (arquivo) values (%s)", (copias[-1].name,))
        conn.commit()
    print(f"{len(elementos)} elementos do OSM ({copias[-1].name})")


if __name__ == "__main__":
    main()
