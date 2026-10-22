"""Carrega quem vive e o que funciona em volta da linha em Juiz de Fora.

Um trecho com muitos atropelamentos pode ser só um trecho com muita gente. Para
separar uma coisa da outra, a análise precisa de três camadas:

- população por setor censitário do Censo 2022 (IBGE, malha com atributos);
- escolas em funcionamento do Censo Escolar 2023, geocodificadas pelo IPEA
  (pacote geobr): onde há crianças;
- os endereços não residenciais do CNEFE 2022 (IBGE): comércio e serviço,
  saúde e templos. O Censo conta quem mora, e o centro de Juiz de Fora é
  comercial: sem isso, um trecho do centro pareceria perigoso demais para a
  gente que mora em volta.

O CNES foi descartado para saúde: o geobr põe na sede do município todo
estabelecimento cuja coordenada não confere, e em Juiz de Fora 1.621 dos 2.096
registros estão nesse ponto, a 1 km da estação central. No CNEFE de Juiz de
Fora, só 3 dos 307.905 endereços não têm a coordenada do próprio endereço ou
da face de quadra.

Os originais são de Minas inteira (setores) ou do Brasil inteiro (escolas) e
passam de 280 MB. Como as fontes são fixas, o repositório guarda só o recorte
de Juiz de Fora em ingest/exposicao_jf/, e a carga lê o recorte. Para refazê-lo
dos originais, rode com --baixar.

Do CNEFE o recorte guarda só a espécie e a coordenada: o endereço e o nome do
estabelecimento (que num MEI é o nome de uma pessoa) não entram.
"""

import csv
import gzip
import io
import sqlite3
import struct
import sys
import zipfile
from pathlib import Path

import requests

from db import conectar

PASTA = Path(__file__).resolve().parent / "exposicao_jf"
CACHE = Path(__file__).resolve().parent / ".cache" / "exposicao_jf"
COD_JF = "3136702"
ORIGENS = {
    "setores": "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/"
               "malha_com_atributos/setores/gpkg/UF/MG/MG_setores_CD2022.gpkg",
    "escolas": "https://www.ipea.gov.br/geobr/data_gpkg/schools/2023/schools_2023.gpkg",
    "enderecos": "https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/"
                 "Censo_Demografico_2022/Arquivos_CNEFE/CSV/Municipio/31_MG/3136702_JUIZ_DE_FORA.zip",
}
# Espécies do CNEFE que não são moradia nem obra: 4 ensino, 5 saúde, 6 outras
# finalidades (comércio e serviço), 8 religioso.
ESPECIES = {"4": "ensino", "5": "saúde", "6": "comércio e serviço", "8": "religioso"}
# Nível de geocodificação: 1 a 3 é o endereço, 4 a face de quadra; 5 e 6
# (localidade e setor) são imprecisos demais para 500 m.
NIVEIS_ACEITOS = {"1", "2", "3", "4"}

DDL = """
create schema if not exists raw;
create table if not exists raw.setores_jf (cd_setor text primary key, situacao text, pessoas int, geom geometry(MultiPolygon, 4674));
create table if not exists raw.escolas_jf (code_school text primary key, name_school text, admin_category text, education_level text, geom geometry(Point, 4674));
-- Um endereço pode ter mais de um uso (comércio e saúde no mesmo número): 127
-- endereços de Juiz de Fora aparecem com duas ou três espécies.
create table if not exists raw.enderecos_jf (
    endereco_id bigint, especie text, geom geometry(Point, 4674), primary key (endereco_id, especie)
);
"""


def wkb_do_gpkg(blob):
    """Tira o cabeçalho do GeoPackage e devolve o WKB, ou None se vazio."""
    if blob is None:
        return None
    flags = blob[3]
    if flags & 0b10000:  # geometria vazia
        return None
    envelope = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(flags >> 1) & 0b111]
    wkb = blob[8 + envelope:]
    # Ponto vazio pode vir como POINT(NaN NaN) sem a flag.
    if len(wkb) == 21 and any(v != v for v in struct.unpack("<dd" if wkb[0] == 1 else ">dd", wkb[5:21])):
        return None
    return wkb


def baixar(nome):
    """Baixa o original para o cache; GeoPackage volta aberto, zip volta como caminho."""
    CACHE.mkdir(parents=True, exist_ok=True)
    destino = CACHE / Path(ORIGENS[nome]).name
    if not destino.exists():
        print(f"baixando {destino.name}")
        with requests.get(ORIGENS[nome], stream=True, timeout=300, headers={"User-Agent": "Mozilla/5.0"}) as resp:
            resp.raise_for_status()
            with destino.open("wb") as arq:
                for bloco in resp.iter_content(1 << 20):
                    arq.write(bloco)
    return destino if destino.suffix == ".zip" else sqlite3.connect(destino)


def gravar(nome, cabecalho, linhas):
    PASTA.mkdir(exist_ok=True)
    with gzip.open(PASTA / f"{nome}.csv.gz", "wt", encoding="utf-8", newline="") as arq:
        escritor = csv.writer(arq)
        escritor.writerow(cabecalho)
        escritor.writerows(sorted(linhas))
    print(f"{nome}: {len(linhas)} linhas no recorte")


def refazer_recortes():
    db = baixar("setores")
    gravar("setores", ["cd_setor", "situacao", "pessoas", "wkb"], [
        (cd, sit, pessoas, wkb_do_gpkg(g).hex())
        for cd, sit, pessoas, g in db.execute(
            "select CD_SETOR, SITUACAO, v0001, geom from MG_setores_CD2022 where CD_MUN = ?", (COD_JF,))
    ])

    db = baixar("escolas")
    gravar("escolas", ["code_school", "name_school", "admin_category", "education_level", "wkb"], [
        (str(cod), nome, adm, nivel or "", wkb.hex())
        for cod, nome, adm, nivel, g in db.execute(
            """select code_school, name_school, admin_category, education_level, geom from schools_2023
               where abbrev_state = 'MG' and name_muni = 'Juiz de Fora'
                 and service_restriction like 'ESCOLA EM FUNCIONAMENTO%'""")
        if (wkb := wkb_do_gpkg(g)) is not None
    ])

    zip_cnefe = baixar("enderecos")
    with zipfile.ZipFile(zip_cnefe) as z, z.open(z.namelist()[0]) as bruto:
        leitor = csv.DictReader(io.TextIOWrapper(bruto, encoding="latin-1"), delimiter=";")
        gravar("enderecos", ["endereco_id", "especie", "lat", "lon"], [
            (int(r["COD_UNICO_ENDERECO"]), ESPECIES[r["COD_ESPECIE"]], r["LATITUDE"], r["LONGITUDE"])
            for r in leitor
            if r["COD_ESPECIE"] in ESPECIES and r["NV_GEO_COORD"] in NIVEIS_ACEITOS
        ])


def ler(nome):
    with gzip.open(PASTA / f"{nome}.csv.gz", "rt", encoding="utf-8", newline="") as arq:
        return list(csv.DictReader(arq))


def main():
    if "--baixar" in sys.argv:
        refazer_recortes()
    setores, escolas, enderecos = ler("setores"), ler("escolas"), ler("enderecos")
    with conectar() as conn:
        conn.execute(DDL)
        conn.execute("truncate raw.setores_jf, raw.escolas_jf, raw.enderecos_jf")
        with conn.cursor() as cur:
            cur.executemany(
                "insert into raw.setores_jf values (%s, %s, %s, st_multi(st_geomfromwkb(decode(%s, 'hex'), 4674)))",
                [(r["cd_setor"], r["situacao"], int(r["pessoas"]), r["wkb"]) for r in setores])
            cur.executemany(
                "insert into raw.escolas_jf values (%s, %s, %s, %s, st_geomfromwkb(decode(%s, 'hex'), 4674))",
                [(r["code_school"], r["name_school"], r["admin_category"], r["education_level"] or None, r["wkb"]) for r in escolas])
            cur.executemany(
                "insert into raw.enderecos_jf values (%s, %s, st_point(%s, %s, 4674))",
                [(int(r["endereco_id"]), r["especie"], float(r["lon"]), float(r["lat"])) for r in enderecos])
        conn.commit()
    print(f"{len(setores)} setores, {len(escolas)} escolas, {len(enderecos)} endereços não residenciais")


if __name__ == "__main__":
    main()
