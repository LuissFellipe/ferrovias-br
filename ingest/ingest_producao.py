"""Carrega a produção ferroviária por origem e destino (SIADE/ANTT) desde 2006.

A ANTT publica um CSV por ano no portal de dados abertos (CKAN). O arquivo do
ano corrente é substituído a cada mês fechado, então a API do CKAN informa a
data de modificação de cada recurso e um arquivo só é baixado de novo quando
ela muda. O raw guarda o texto como veio: a conversão de número e data fica
no dbt, onde ela pode ser testada.

No GitHub Actions o banco nasce vazio, e baixar os 21 CSVs do portal da ANTT
levava cerca de 9 minutos. Cada CSV baixado fica guardado em ingest/.cache/,
com a data de modificação do CKAN no nome, e o workflow preserva essa pasta
entre execuções. Um arquivo só vem do cache se o CKAN ainda informa a mesma
data; em 02/10/2026 a ANTT republicou os 21 anos de uma vez, e uma cópia fixa
teria ficado desatualizada sem aviso.
"""

import csv
import io
import json
import re
import time
from pathlib import Path

import requests

from db import conectar

CKAN = "https://dados.antt.gov.br/api/3/action/package_show"
CACHE = Path(__file__).resolve().parent / ".cache"
CONJUNTO = "sistema-de-acompanhamento-do-desempenho-operacional-das-concessionarias-siade"
ANO_INICIAL = 2006
CABECALHO = [
    "Mes_Ano", "Ferrovia", "Mercadoria_ANTT", "Estacao_Origem", "UF_Origem",
    "Estacao_Destino", "UF_Destino", "TU", "TKU",
]

DDL = """
create schema if not exists raw;
create table if not exists raw.producao (
    arquivo text not null,
    linha int not null,
    mes_ano text not null,
    ferrovia text not null,
    mercadoria text not null,
    estacao_origem text not null,
    uf_origem text not null,
    estacao_destino text not null,
    uf_destino text not null,
    tu text not null,
    tku text not null,
    carregado_em timestamptz not null default now(),
    primary key (arquivo, linha)
);
create table if not exists raw.arquivos_carregados (
    arquivo text primary key,
    modificado_em text not null,
    linhas int not null,
    carregado_em timestamptz not null default now()
);
"""

COLUNAS = [
    "arquivo", "linha", "mes_ano", "ferrovia", "mercadoria", "estacao_origem",
    "uf_origem", "estacao_destino", "uf_destino", "tu", "tku",
]


def requisitar(url, tentativas=8, **kwargs):
    # O portal da ANTT derruba conexões com frequência, e às vezes passa
    # minutos sem responder: em 21/10/2026 o GitHub Actions esgotou 5
    # tentativas com esperas de 2 a 16 s no CSV de 2012. A espera agora
    # cresce até 2 minutos.
    for tentativa in range(1, tentativas + 1):
        try:
            resp = requests.get(url, timeout=120, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as erro:
            if tentativa == tentativas:
                raise
            espera = min(2 ** (tentativa + 1), 120)
            print(f"falha na ANTT ({erro.__class__.__name__}), nova tentativa em {espera}s")
            time.sleep(espera)


def arquivos_a_carregar():
    # A descrição dos recursos vem com caracteres de controle crus, que o
    # json estrito recusa.
    pacote = json.loads(requisitar(CKAN, params={"id": CONJUNTO}).text, strict=False)["result"]
    arquivos = {}
    for recurso in pacote["resources"]:
        m = re.fullmatch(r"Produção Origem Destino (\d{4})", recurso["name"].strip())
        if recurso["format"] != "CSV" or not m or int(m.group(1)) < ANO_INICIAL:
            continue
        nome = recurso["url"].rsplit("/", 1)[-1]
        arquivos[int(m.group(1))] = {
            "nome": nome,
            "url": recurso["url"],
            "modificado": recurso["last_modified"] or recurso["created"],
        }
    faltando = [a for a in range(ANO_INICIAL, max(arquivos) + 1) if a not in arquivos]
    if faltando:
        raise RuntimeError(f"a ANTT não tem o CSV de {faltando}")
    return [arquivos[a] for a in sorted(arquivos)]


def ler(conteudo, nome):
    texto = conteudo.decode("latin1")
    leitor = csv.reader(io.StringIO(texto), delimiter=";")
    cabecalho = [c.strip() for c in next(leitor)]
    # Os 21 anos têm hoje o mesmo layout. Se a ANTT mudar uma coluna, a carga
    # para aqui em vez de gravar valores na coluna errada.
    if cabecalho != CABECALHO:
        raise RuntimeError(f"{nome}: cabeçalho mudou para {cabecalho}")
    for i, linha in enumerate(leitor, start=2):
        if not any(c.strip() for c in linha):
            continue
        if len(linha) != len(CABECALHO):
            raise RuntimeError(f"{nome}, linha {i}: {len(linha)} colunas")
        yield (nome, i, *(c.strip() for c in linha))


def baixar(arquivo):
    versao = re.sub(r"[^0-9A-Za-z]", "", arquivo["modificado"])
    guardado = CACHE / f"{arquivo['nome']}.{versao}"
    if guardado.exists():
        return guardado.read_bytes()
    conteudo = requisitar(arquivo["url"]).content
    CACHE.mkdir(exist_ok=True)
    # Sai a versão anterior do mesmo arquivo, para o cache não crescer a cada
    # republicação.
    for antigo in CACHE.glob(f"{arquivo['nome']}.*"):
        antigo.unlink()
    guardado.write_bytes(conteudo)
    return conteudo


def carregar(conn, arquivo):
    nome = arquivo["nome"]
    linhas = list(ler(baixar(arquivo), nome))
    with conn.transaction():
        # O arquivo substitui por inteiro o que ele mesmo carregou antes: uma
        # revisão da ANTT num mês passado também chega aqui.
        conn.execute("delete from raw.producao where arquivo = %s", (nome,))
        with conn.cursor().copy(f"copy raw.producao ({', '.join(COLUNAS)}) from stdin") as copy:
            for linha in linhas:
                copy.write_row(linha)
        conn.execute(
            """insert into raw.arquivos_carregados (arquivo, modificado_em, linhas)
               values (%s, %s, %s)
               on conflict (arquivo) do update set modificado_em = excluded.modificado_em,
                   linhas = excluded.linhas, carregado_em = now()""",
            (nome, arquivo["modificado"], len(linhas)),
        )
    return len(linhas)


def main():
    with conectar() as conn:
        conn.autocommit = True
        conn.execute(DDL)
        ja_carregados = dict(
            conn.execute("select arquivo, modificado_em from raw.arquivos_carregados").fetchall()
        )
        for arquivo in arquivos_a_carregar():
            if ja_carregados.get(arquivo["nome"]) == arquivo["modificado"]:
                continue
            n = carregar(conn, arquivo)
            print(f"{arquivo['nome']}: {n} linhas")


if __name__ == "__main__":
    main()
