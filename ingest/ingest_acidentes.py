"""Carrega os acidentes ferroviários (RAAF/ANTT) e o índice oficial de acidentes.

Os registros vêm em dois arquivos com layouts diferentes: 2004 a novembro de
2020 (22 colunas) e de dezembro de 2020 em diante (27 colunas). O segundo é
republicado de tempos em tempos com um período maior e o mesmo começo, então
de cada série vale só o arquivo mais recente. Em outubro de 2026, a versão até
junho de 2025 e a versão até janeiro de 2026 tinham as mesmas 3.305 linhas em
comum, sem nenhum campo alterado.

A data de ocorrência não tem formato único. No arquivo de 2004 é DD/MM/AAAA,
como diz o dicionário. No arquivo de dezembro de 2020 em diante, toda data com
dia até 12 veio como MM/DD/AAAA (1º de dezembro de 2020 está como
"12/01/2020") e as demais como DD/MM. Lido de um jeito só, 1.345 das 3.710
linhas (36%) cairiam na data errada. O formato de cada arquivo é decidido aqui pela ordem do
próprio arquivo, e a carga para se a decisão não for unânime.

A coluna Equipagem traz o nome do maquinista. Ela não é carregada.
"""

import bisect
import calendar
import csv
import io
import json
import re
from datetime import date

from db import conectar
from ingest_producao import requisitar

CKAN = "https://dados.antt.gov.br/api/3/action/package_show"
CONJUNTO = "relatorio-de-acompanhamento-de-acidentes-ferroviarios-raaf"

# Cabeçalho da ANTT → coluna no raw. None: a coluna é descartada.
COLUNAS_ANTT = {
    "Gravidade": "gravidade",
    "Concessionaria": "ferrovia",
    "Data_Ocorrencia": "data_ocorrencia",
    "Hora_Ocorrencia": "hora_ocorrencia",
    "UF": "uf",
    "Municipio": "municipio",
    "Linha": "linha_ferrea",
    "Quilômetro_Inicial": "km_inicial",
    "Quilômetro_Final": "km_final",
    "Estação_Anterior": "estacao_anterior",
    "Estação_Posterior": "estacao_posterior",
    "Perímetro_Urbano": "perimetro_urbano",
    "Causa_direta": "causa_direta",
    "Causa_contibutiva": "causa_contributiva",
    "Natureza": "natureza",
    "Interrupção": "interrupcao",
    "N_Trem": "n_trens",
    "Prefixo": "prefixo",
    "Double_Stack": "double_stack",
    "Serviço_Transporte": "servico_transporte",
    "N_feridos": "feridos",
    "N_obitos": "obitos",
    "Mercadoria": "mercadoria",
    "Equipagem": None,
    "Outra_Ferrovia": "outra_ferrovia",
    "PN": "passagem_em_nivel",
    "Prejuízo_Financeiro": "prejuizo",
}
# Os dois layouts publicados. Um terceiro para a carga.
LAYOUTS = {
    22: [
        "Gravidade", "Concessionaria", "Data_Ocorrencia", "Hora_Ocorrencia", "UF", "Municipio",
        "Linha", "Quilômetro_Inicial", "Estação_Anterior", "Estação_Posterior", "Perímetro_Urbano",
        "Causa_direta", "Natureza", "Interrupção", "Prefixo", "Serviço_Transporte", "N_feridos",
        "N_obitos", "Mercadoria", "Equipagem", "Outra_Ferrovia", "PN",
    ],
    27: [
        "Gravidade", "Concessionaria", "Data_Ocorrencia", "Hora_Ocorrencia", "UF", "Municipio",
        "Linha", "Quilômetro_Inicial", "Quilômetro_Final", "Estação_Anterior", "Estação_Posterior",
        "Perímetro_Urbano", "Causa_direta", "Causa_contibutiva", "Natureza", "Interrupção", "N_Trem",
        "Prefixo", "Double_Stack", "Serviço_Transporte", "N_feridos", "N_obitos", "Mercadoria",
        "Equipagem", "Outra_Ferrovia", "PN", "Prejuízo_Financeiro",
    ],
}
COLUNAS = [c for c in COLUNAS_ANTT.values() if c]
CABECALHO_INDICE = ["concessionaria", "ano", "indice_de_acidentes_por_milhao_de_trem_km"]

DDL = f"""
create schema if not exists raw;
create table if not exists raw.acidentes (
    arquivo text not null,
    linha int not null,
    {", ".join(f"{c} text" for c in COLUNAS)},
    carregado_em timestamptz not null default now(),
    primary key (arquivo, linha)
);
create table if not exists raw.acidentes_arquivos (
    arquivo text primary key,
    periodo_inicio date not null,
    periodo_fim date not null,
    formato_data text not null,
    datas_ambiguas int not null,
    modificado_em text not null,
    linhas int not null,
    carregado_em timestamptz not null default now()
);
create table if not exists raw.indice_acidentes (
    arquivo text not null,
    linha int not null,
    concessionaria text not null,
    ano text not null,
    indice text not null,
    carregado_em timestamptz not null default now(),
    primary key (arquivo, linha)
);
create table if not exists raw.indice_acidentes_arquivos (
    arquivo text primary key,
    ano_final int not null,
    modificado_em text not null,
    linhas int not null,
    carregado_em timestamptz not null default now()
);
"""

MESES = {
    m: i for i, m in enumerate(
        ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"], start=1)
}


def limite(texto, fim):
    # "2004", "Dezembro de 2020", "Janeiro de 2026". O fim de um período só
    # com o ano é dezembro.
    partes = texto.strip().lower().split(" de ")
    ano = int(partes[-1])
    mes = MESES[partes[0]] if len(partes) == 2 else (12 if fim else 1)
    return date(ano, mes, calendar.monthrange(ano, mes)[1] if fim else 1)


def recursos():
    pacote = json.loads(requisitar(CKAN, params={"id": CONJUNTO}).text, strict=False)["result"]
    series, indices = {}, []
    for recurso in pacote["resources"]:
        if recurso["format"] != "CSV":
            continue
        nome = recurso["url"].rsplit("/", 1)[-1]
        base = {"nome": nome, "url": recurso["url"], "modificado": recurso["last_modified"] or recurso["created"]}
        titulo = recurso["name"].strip()
        # O portal escreve "á" onde seria "a": "2004 á Novembro de 2020".
        if m := re.fullmatch(r"Acidentes Ferroviários - (.+?) [áa] (.+)", titulo):
            arq = {**base, "inicio": limite(m.group(1), False), "fim": limite(m.group(2), True)}
            atual = series.get(arq["inicio"])
            if not atual or (arq["fim"], arq["modificado"]) > (atual["fim"], atual["modificado"]):
                series[arq["inicio"]] = arq
        elif m := re.fullmatch(r"Índice de Acidentes Ferroviários de \d{4} a (\d{4})", titulo):
            indices.append({**base, "ano_final": int(m.group(1))})
    if not series or not indices:
        raise RuntimeError("o conjunto RAAF não tem mais os recursos esperados")
    return [series[s] for s in sorted(series)], indices


def formato_das_datas(datas, nome):
    """Decide entre DD/MM e "misto" (MM/DD quando o dia vai até 12).

    Uma data como 13/12/2020 só tem uma leitura. Uma como 12/01/2020 tem duas,
    e vale a que fica mais perto das datas sem ambiguidade vizinhas no arquivo,
    que vem em ordem cronológica por trechos.
    """
    partes = [tuple(map(int, d.split("/"))) for d in datas]
    certas = [i for i, (a, b, _) in enumerate(partes) if a > 12 or b > 12]
    ordinal = {i: date(partes[i][2], partes[i][1], partes[i][0]).toordinal() for i in certas}
    votos = {"DD/MM": 0, "misto": 0}
    for i, (a, b, ano) in enumerate(partes):
        if a > 12 or b > 12 or a == b:
            continue
        k = bisect.bisect(certas, i)
        vizinhas = [ordinal[certas[j]] for j in (k - 1, k) if 0 <= j < len(certas)]
        distancia = lambda d: min(abs(d.toordinal() - v) for v in vizinhas)
        dd, mm = distancia(date(ano, b, a)), distancia(date(ano, a, b))
        if dd != mm:
            votos["DD/MM" if dd < mm else "misto"] += 1
    total = sum(votos.values())
    vencedor = max(votos, key=votos.get)
    if total and votos[vencedor] < 0.99 * total:
        raise RuntimeError(f"{nome}: formato de data indefinido ({votos})")
    return vencedor, total


def ler_acidentes(conteudo, nome):
    leitor = csv.reader(io.StringIO(conteudo.decode("latin1")), delimiter=";")
    cabecalho = [c.strip() for c in next(leitor)]
    if LAYOUTS.get(len(cabecalho)) != cabecalho:
        raise RuntimeError(f"{nome}: layout novo: {cabecalho}")
    destino = [COLUNAS_ANTT[c] for c in cabecalho]
    linhas = []
    for i, linha in enumerate(leitor, start=2):
        if not any(c.strip() for c in linha):
            continue
        if len(linha) != len(cabecalho):
            raise RuntimeError(f"{nome}, linha {i}: {len(linha)} colunas")
        registro = dict.fromkeys(COLUNAS)
        for col, valor in zip(destino, linha):
            if col:
                registro[col] = valor.strip() or None
        linhas.append((nome, i, *(registro[c] for c in COLUNAS)))
    return linhas


def carregar_acidentes(conn, arq, outros_da_serie):
    nome = arq["nome"]
    linhas = ler_acidentes(requisitar(arq["url"]).content, nome)
    formato, ambiguas = formato_das_datas([r[2 + COLUNAS.index("data_ocorrencia")] for r in linhas], nome)
    with conn.transaction():
        # Uma versão mais nova da série substitui a anterior por inteiro.
        conn.execute("delete from raw.acidentes where arquivo = any(%s)", ([nome, *outros_da_serie],))
        conn.execute("delete from raw.acidentes_arquivos where arquivo = any(%s)", ([nome, *outros_da_serie],))
        with conn.cursor().copy(f"copy raw.acidentes (arquivo, linha, {', '.join(COLUNAS)}) from stdin") as copy:
            for linha in linhas:
                copy.write_row(linha)
        conn.execute(
            """insert into raw.acidentes_arquivos
               (arquivo, periodo_inicio, periodo_fim, formato_data, datas_ambiguas, modificado_em, linhas)
               values (%s, %s, %s, %s, %s, %s, %s)""",
            (nome, arq["inicio"], arq["fim"], formato, ambiguas, arq["modificado"], len(linhas)),
        )
    return len(linhas), formato


def carregar_indice(conn, arq):
    nome = arq["nome"]
    leitor = csv.reader(io.StringIO(requisitar(arq["url"]).content.decode("latin1")), delimiter=";")
    cabecalho = [c.strip() for c in next(leitor)]
    if cabecalho != CABECALHO_INDICE:
        raise RuntimeError(f"{nome}: cabeçalho mudou para {cabecalho}")
    linhas = [(nome, i, *(c.strip() for c in l)) for i, l in enumerate(leitor, start=2) if any(c.strip() for c in l)]
    with conn.transaction():
        conn.execute("delete from raw.indice_acidentes where arquivo = %s", (nome,))
        with conn.cursor().copy("copy raw.indice_acidentes (arquivo, linha, concessionaria, ano, indice) from stdin") as copy:
            for linha in linhas:
                copy.write_row(linha)
        conn.execute(
            """insert into raw.indice_acidentes_arquivos (arquivo, ano_final, modificado_em, linhas)
               values (%s, %s, %s, %s)
               on conflict (arquivo) do update set ano_final = excluded.ano_final,
                   modificado_em = excluded.modificado_em, linhas = excluded.linhas, carregado_em = now()""",
            (nome, arq["ano_final"], arq["modificado"], len(linhas)),
        )
    return len(linhas)


def main():
    series, indices = recursos()
    with conectar() as conn:
        conn.autocommit = True
        conn.execute(DDL)
        carregados = dict(conn.execute("select arquivo, modificado_em from raw.acidentes_arquivos").fetchall())
        por_serie = {}
        for arquivo, inicio in conn.execute("select arquivo, periodo_inicio from raw.acidentes_arquivos"):
            por_serie.setdefault(inicio, []).append(arquivo)
        for arq in series:
            if carregados.get(arq["nome"]) == arq["modificado"]:
                continue
            outros = [a for a in por_serie.get(arq["inicio"], []) if a != arq["nome"]]
            n, formato = carregar_acidentes(conn, arq, outros)
            print(f"{arq['nome']}: {n} acidentes, data {formato}, {arq['inicio']} a {arq['fim']}")

        carregados = dict(conn.execute("select arquivo, modificado_em from raw.indice_acidentes_arquivos").fetchall())
        for arq in indices:
            if carregados.get(arq["nome"]) == arq["modificado"]:
                continue
            n = carregar_indice(conn, arq)
            # Em abril de 2026 a ANTT publicou o índice "de 2006 a 2025" só com
            # o cabeçalho. O staging usa, ano a ano, o arquivo mais novo que
            # tem o número.
            print(f"{arq['nome']}: {n} linhas de índice" + (" (arquivo vazio)" if not n else ""))


if __name__ == "__main__":
    main()
