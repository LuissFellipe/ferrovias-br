# Carga nas Ferrovias do Brasil

Pipeline ELT que coleta a **produção ferroviária por origem e destino** que as concessionárias declaram à ANTT, de 2006 até hoje. Ele localiza cada estação no mapa, transforma os dados com dbt e publica um **painel de fluxos** no GitHub Pages. O foco é a **MRS Logística**.

**🚆 Painel:** https://luissfellipe.github.io/ferrovias-br/ · **📚 Documentação do dbt:** https://luissfellipe.github.io/ferrovias-br/dbt/

![Painel com os fluxos da MRS em 2025](docs/painel.png)

**Pergunta:** o que as ferrovias transportam, de onde para onde, e como isso mudou em 20 anos?

Projeto independente, feito com dados públicos e sem vínculo com a MRS ou com a ANTT.

## Arquitetura

```
ANTT, SIADE (CKAN, 21 CSVs anuais) ─► ingest_producao.py ─┐
InfraSA, pátios ferroviários (ArcGIS) ─► ingest_patios.py ─┴─► PostGIS (raw) ─► dbt ─► export_site.py ─► painel estático
                                                                       staging            JSON           MapLibre + deck.gl
                                                                       intermediate                      (GitHub Pages)
                                                                       marts ─► notebooks de análise
                   GitHub Actions: toda semana, do zero, com testes antes de publicar
```

| Camada | Objeto | Descrição |
|---|---|---|
| raw | `raw.producao` | Uma linha do CSV da ANTT por registro, com o texto como veio |
| raw | `raw.patios` | 2.110 pátios declarados pelas concessionárias, com coordenada |
| raw | `raw.arquivos_carregados` | Cada CSV e a data de modificação dele no CKAN |
| staging | `stg_antt__producao`, `stg_infrasa__patios` | Data, número no padrão brasileiro e nome de estação normalizado |
| intermediate | `int_producao__deduplicada` | Sem as repetições idênticas publicadas pela ANTT |
| intermediate | `int_estacoes__geolocalizadas` | Cada estação do SIADE com o pátio correspondente |
| marts | `dim_estacoes`, `dim_ferrovias`, `dim_mercadorias` | Estação com coordenada, concessionária e mercadoria com grupo |
| marts | `fct_producao_mensal` | Um fluxo por mês, ferrovia, mercadoria, origem e destino |
| marts | `fct_fluxos_anuais`, `fct_ferrovia_grupo_mensal` | Agregados que o painel e os notebooks leem |

## O que os dados mostram

| | 2006 | 2018 | 2019 | 2025 |
|---|---|---|---|---|
| MRS, toneladas úteis | 102,0 mi | 136,6 mi | **106,0 mi** | **153,2 mi** |

- **Brumadinho derrubou a MRS em 22% em 2019.** Depois de 25/01/2019, a estação de Córrego do Feijão não embarca mais nada. Mas ela perdeu 7,6 mi t entre fevereiro e dezembro, e **Otávio Dapieve perdeu 33,5 mi t** no mesmo período. A queda foi muito maior que a mina que rompeu. A MRS só voltou ao nível de 2018 em 2023 e bateu o recorde da série em 2025.
- **A carga se mudou de terminal.** O Guaíba era o principal destino do minério em 2006, com 45,4 mi t. Caiu para 20,4 mi t em 2019 e recebeu 31,6 mi t em 2025. A Baía de Sepetiba foi de 22,4 para 57,4 mi t, e o Porto Sudeste, que começa em 2017, chegou a 17,3 mi t.
- **A dependência do minério não mudou.** A carga geral cresceu 40% entre 2006 e 2024, mas o minério cresceu junto, e a fatia dele ficou entre 80% e 87% durante os 20 anos. Fora do minério, o que mais cresceu foi açúcar (que começa em 2007), celulose e madeira, e grãos.
- **A MRS é a 2ª ferrovia do país em tonelagem** (153,2 mi t em 2025, atrás da Carajás, com 177,7 mi t), com distância média de 468 km por tonelada. A Carajás tem 907 km e a Rumo Malha Norte, 1.487 km.

A análise completa está em [`analises/02_mrs.ipynb`](analises/02_mrs.ipynb), e a investigação da fonte em [`analises/01_reconhecimento.ipynb`](analises/01_reconhecimento.ipynb).

## Decisões técnicas

- **Coordenadas dos pátios oficiais, não do OpenStreetMap.** O SIADE identifica a estação só por nome e UF. O OSM cobria 18% da tonelagem da MRS e casava nomes errados ("Floriano" com Marechal Floriano, no ES). A camada de pátios declarados à ANTT, publicada pela InfraSA, casa 524 das 533 estações pelo nome. Com uma correção manual, cobre 99,97% da carga, incluindo todas as estações da MRS.
- **A física confere a geolocalização.** O trilho entre duas estações nunca é mais curto que a linha reta. Um teste do dbt compara a linha reta com a distância ferroviária de cada rota (TKU ÷ TU). Para conferir que o teste pega erro de verdade, a Baía de Sepetiba foi colocada em Manaus, e o teste falhou.
- **Três defeitos da camada de pátios tratados no staging.** 245 pátios têm coordenada `NaN`, que o Postgres não trata como nulo. Estações na divisa entre estados aparecem com UF diferente na ANTT e na InfraSA (Jupiá, MS ou SP; São Simão, GO ou MG); nesse caso, vale o pátio de mesmo nome e da mesma ferrovia. Um nome com erro de digitação foi para `seeds/estacoes_manuais.csv`.
- **A distância de cada rota tem de ser estável.** 93% da carga fica a menos de 1% da distância mediana da própria rota. O teste falha se mais de 0,5% da carga desviar mais de 50%, o que indicaria TU e TKU trocados ou uma unidade nova num arquivo.
- **A carga para se o layout mudar.** Os 21 anos têm o mesmo cabeçalho. Se a ANTT renomear ou mover uma coluna, a ingestão para em vez de gravar valor na coluna errada. O raw guarda o texto como veio, e a conversão de número fica no dbt, onde dá para testar.
- **Duplicata idêntica sai; duplicata diferente para o pipeline.** O CSV de 2019 traz dezembro da Rumo Malha Sul duas vezes, com 34 registros idênticos. Se aparecer uma repetição com valores diferentes, o teste de chave única falha, porque não há como saber qual das duas vale.
- **Mercadoria nova precisa ser classificada.** Uma mercadoria que não está em `seeds/mercadorias.csv` fica com o grupo nulo, e um teste para o pipeline até ela ser classificada.
- **"Ferrovia" é a concessionária responsável, não o trilho.** O dicionário da ANTT define assim, e por isso aparecem na conta da MRS fluxos de Pederneiras e Votuporanga para Santos, que rodam em malha de outra concessionária.
- **O ano em andamento é comparado com os mesmos meses do ano anterior.** Em 2026, o painel compara jan–ago com jan–ago de 2025, e não com o ano de 2025 inteiro.
- **Notebooks só leem os marts.** Nenhuma regra de limpeza mora nos notebooks, então o número deles é o mesmo do painel.

## Achado de qualidade de dados

A mercadoria **"Minério de Ferro Especial – MRS distância menor 100 km"** cumpre o próprio nome até 2017. Em 2024, **94% da tonelagem dela viajou mais de 100 km**, com fluxos de até 635 km. Para as análises não muda nada, porque ela entra em "Minério de ferro" e a distância vem sempre de TKU ÷ TU, nunca do nome. Mas o nome não descreve mais o que a ANTT põe nessa linha.

## Como rodar

Requisitos: Docker e [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env
uv sync
make pipeline        # sobe o PostGIS, ingere, roda dbt build (modelos + testes) e exporta o painel
make site            # serve o painel em http://localhost:8001
make analise         # abre os notebooks no Jupyter Lab
```

Outros alvos: `make ingest`, `make transform`, `make export`, `make docs` e `make down`.

## Fontes

- Produção origem-destino: [ANTT, SIADE](https://dados.antt.gov.br/dataset/sistema-de-acompanhamento-do-desempenho-operacional-das-concessionarias-siade)
- Pátios ferroviários: [InfraSA](https://geo.infrasa.gov.br/server/rest/services/P%C3%A1tio_Ferrovi%C3%A1rio/MapServer)
- Mapa base: © [CARTO](https://carto.com/), © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors
