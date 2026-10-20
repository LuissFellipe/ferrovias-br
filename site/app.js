// Painel da carga ferroviária. Tudo é calculado no navegador a partir de
// quatro arquivos: os fluxos anuais (origem → destino por mercadoria), a série
// mensal por ferrovia e grupo, as estações e o meta.json com as listas que os
// índices dos outros arquivos apontam.

const CORES = [[57, 135, 229], [25, 158, 112], [217, 89, 38], [138, 138, 146]];
const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
// Marcos que explicam quebras na série. Só aparecem nas ferrovias afetadas.
const EVENTOS = [
  { mes: 201901, texto: "Brumadinho", ferrovias: ["MRS", "EFVM"] },
];

let meta, estacoes, fluxos, serie;
let grupoDaMercadoria, categoriaDoGrupo;
let mapa, overlay;
let estado = { ferrovia: -1, ano: 0, grupo: -1, estacao: -1 };
let selecao = [];      // fluxos do recorte, já filtrados
let rotaEmFoco = null; // rota destacada ao passar o mouse na lista

const $ = (id) => document.getElementById(id);

async function json(caminho) {
  const resp = await fetch(caminho);
  if (!resp.ok) throw new Error(`${caminho}: ${resp.status}`);
  return resp.json();
}

// ---------- formatação ----------

const fmt = (n, casas = 0) => n.toLocaleString("pt-BR", { maximumFractionDigits: casas, minimumFractionDigits: casas });

function toneladas(t) {
  if (t >= 1e6) return `${fmt(t / 1e6, t >= 1e8 ? 0 : 1)} mi t`;
  if (t >= 1e3) return `${fmt(t / 1e3, t >= 1e5 ? 0 : 1)} mil t`;
  return `${fmt(t)} t`;
}

function percentual(fracao) {
  if (fracao > 0 && fracao < 0.001) return "<0,1%";
  return `${fmt(100 * fracao, fracao < 0.1 ? 1 : 0)}%`;
}

const nomeEstacao = (i) => `${estacoes[i][0]} (${estacoes[i][1]})`;
const siglaFerrovia = (i) => meta.ferrovias[i][0];

// ---------- recortes ----------

const ultimoMes = () => Number(meta.ultimo_mes.replace("-", ""));
const anoFinal = () => Math.floor(ultimoMes() / 100);
const mesesNoAno = (ano) => (ano === anoFinal() ? ultimoMes() % 100 : 12);

function passa(f, comEstacao = true, comGrupo = true) {
  if (estado.ferrovia >= 0 && f[1] !== estado.ferrovia) return false;
  if (comGrupo && estado.grupo >= 0 && grupoDaMercadoria[f[2]] !== estado.grupo) return false;
  if (comEstacao && estado.estacao >= 0 && f[3] !== estado.estacao && f[4] !== estado.estacao) return false;
  return true;
}

function calcularSelecao() {
  selecao = fluxos.filter((f) => f[0] === estado.ano && passa(f));
}

// Série mensal do recorte de ferrovia e grupo. Com estação escolhida, a série
// continua sendo a da ferrovia: o SIADE só tem o mês no nível do fluxo, e o
// export manda os fluxos somados por ano.
function serieMensal() {
  const porMes = new Map();
  for (const [mes, fer, gru, tu] of serie) {
    if (estado.ferrovia >= 0 && fer !== estado.ferrovia) continue;
    if (estado.grupo >= 0 && gru !== estado.grupo) continue;
    porMes.set(mes, (porMes.get(mes) || 0) + tu);
  }
  const meses = [];
  for (let a = 2006; a <= anoFinal(); a++) {
    for (let m = 1; m <= mesesNoAno(a); m++) meses.push([a * 100 + m, porMes.get(a * 100 + m) || 0]);
  }
  return meses;
}

function totaisDoAno(ano, ateMes = 12) {
  let tu = 0, tku = 0, minerio = 0;
  for (const [mes, fer, gru, t, tk] of serie) {
    if (Math.floor(mes / 100) !== ano || mes % 100 > ateMes) continue;
    if (estado.ferrovia >= 0 && fer !== estado.ferrovia) continue;
    if (estado.grupo >= 0 && gru !== estado.grupo) continue;
    tu += t; tku += tk;
    if (meta.grupos[gru][0] === "Minério de ferro") minerio += t;
  }
  return { tu, tku, minerio };
}

function totaisDaEstacao(ano) {
  let tu = 0, tku = 0, minerio = 0;
  for (const f of fluxos) {
    if (f[0] !== ano || !passa(f)) continue;
    tu += f[5]; tku += f[6];
    if (meta.grupos[grupoDaMercadoria[f[2]]][0] === "Minério de ferro") minerio += f[5];
  }
  return { tu, tku, minerio };
}

// Fluxos somados por par origem → destino, com a categoria que mais pesa.
function rotas() {
  const porPar = new Map();
  for (const f of selecao) {
    const chave = f[3] * 10000 + f[4];
    let r = porPar.get(chave);
    if (!r) {
      r = { o: f[3], d: f[4], tu: 0, tku: 0, porCat: [0, 0, 0, 0], porMerc: new Map() };
      porPar.set(chave, r);
    }
    r.tu += f[5]; r.tku += f[6];
    r.porCat[categoriaDoGrupo[grupoDaMercadoria[f[2]]]] += f[5];
    r.porMerc.set(f[2], (r.porMerc.get(f[2]) || 0) + f[5]);
  }
  const lista = [...porPar.values()];
  for (const r of lista) r.cat = r.porCat.indexOf(Math.max(...r.porCat));
  return lista.sort((a, b) => b.tu - a.tu);
}

function movimentoPorEstacao() {
  const mov = new Map();
  for (const f of selecao) {
    for (const [i, lado] of [[f[3], "emb"], [f[4], "rec"]]) {
      let m = mov.get(i);
      if (!m) mov.set(i, (m = { emb: 0, rec: 0 }));
      m[lado] += f[5];
    }
  }
  return mov;
}

// ---------- mapa ----------

const temCoord = (i) => estacoes[i][3] !== null;
const posicao = (i) => [estacoes[i][4] / 1e4, estacoes[i][3] / 1e4];

function desenharMapa() {
  const lista = rotas().filter((r) => r.o !== r.d && temCoord(r.o) && temCoord(r.d));
  const max = lista.length ? lista[0].tu : 1;
  const largura = (tu) => 0.6 + 14 * Math.sqrt(tu / max);
  const destacada = (r) => rotaEmFoco && r.o === rotaEmFoco.o && r.d === rotaEmFoco.d;
  // Opacidade acompanha a carga: centenas de fluxos pequenos não podem
  // apagar os corredores que carregam quase tudo.
  const alfa = (r) => (rotaEmFoco ? (destacada(r) ? 255 : 35) : Math.round(70 + 185 * Math.sqrt(r.tu / max)));

  const mov = movimentoPorEstacao();
  const pontos = [...mov.entries()].filter(([i]) => temCoord(i));
  const maxMov = Math.max(1, ...pontos.map(([, m]) => m.emb + m.rec));

  overlay.setProps({
    layers: [
      new deck.ArcLayer({
        id: "rotas",
        // As maiores por último, para ficarem por cima.
        data: lista.slice().reverse(),
        getSourcePosition: (r) => posicao(r.o),
        getTargetPosition: (r) => posicao(r.d),
        getSourceColor: (r) => [...CORES[r.cat], alfa(r)],
        getTargetColor: (r) => [...CORES[r.cat], alfa(r)],
        getWidth: (r) => largura(r.tu),
        getHeight: 0.35,
        widthUnits: "pixels",
        pickable: true,
        autoHighlight: true,
        highlightColor: [255, 255, 255, 90],
        updateTriggers: { getSourceColor: [rotaEmFoco], getTargetColor: [rotaEmFoco] },
        onHover: ({ object, x, y }) => (object ? dica(textoRota(object), x, y) : esconderDica()),
      }),
      new deck.ScatterplotLayer({
        id: "estacoes",
        data: pontos,
        getPosition: ([i]) => posicao(i),
        getRadius: ([i, m]) => (i === estado.estacao ? 9 : 2.5 + 9 * Math.sqrt((m.emb + m.rec) / maxMov)),
        radiusUnits: "pixels",
        getFillColor: ([i]) => (i === estado.estacao ? [255, 255, 255, 255] : [236, 235, 231, 200]),
        getLineColor: [20, 21, 27, 255],
        lineWidthUnits: "pixels",
        getLineWidth: 2,
        stroked: true,
        pickable: true,
        updateTriggers: { getRadius: [estado.estacao], getFillColor: [estado.estacao] },
        onHover: ({ object, x, y }) => (object ? dica(textoEstacao(object[0], object[1]), x, y) : esconderDica()),
        onClick: ({ object }) => object && escolherEstacao(object[0] === estado.estacao ? -1 : object[0]),
      }),
    ],
  });
}

function textoRota(r) {
  const principais = [...r.porMerc.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3)
    .map(([m, tu]) => `${meta.mercadorias[m][0]}: ${toneladas(tu)}`).join("<br>");
  return `<strong>${nomeEstacao(r.o)} → ${nomeEstacao(r.d)}</strong><br>
    ${toneladas(r.tu)} em ${estado.ano} · ${fmt(r.tku / r.tu)} km de trilho<br>
    <span class="t2">${principais}</span>`;
}

function textoEstacao(i, m) {
  return `<strong>${nomeEstacao(i)}</strong><br>
    Embarcou ${toneladas(m.emb)} · recebeu ${toneladas(m.rec)}<br>
    <span class="t2">${i === estado.estacao ? "clique para soltar" : "clique para ver só os fluxos desta estação"}</span>`;
}

function dica(html, x, y) {
  const t = $("tooltip");
  t.innerHTML = html;
  t.hidden = false;
  const larg = t.offsetWidth, alt = t.offsetHeight;
  t.style.left = `${Math.min(x + 14, innerWidth - larg - 8)}px`;
  t.style.top = `${Math.min(y + 14, innerHeight - alt - 8)}px`;
}
const esconderDica = () => ($("tooltip").hidden = true);

function margens() {
  if (innerWidth <= 720) return { top: 40, bottom: innerHeight * 0.52, left: 30, right: 30 };
  return { top: 50, bottom: 50, left: 410, right: 50 };
}

function enquadrar() {
  const pts = [];
  for (const f of selecao) for (const i of [f[3], f[4]]) if (temCoord(i)) pts.push(posicao(i));
  if (!pts.length) return;
  const lons = pts.map((p) => p[0]), lats = pts.map((p) => p[1]);
  mapa.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]],
    { padding: margens(), maxZoom: 9, duration: 800 });
}

// ---------- painel ----------

function svg(tag, attrs, pai) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  if (pai) pai.appendChild(el);
  return el;
}

function desenharSerie() {
  const el = $("serie");
  el.replaceChildren();
  const larg = el.clientWidth, alt = el.clientHeight;
  const m = { t: 16, r: 4, b: 16, l: 34 };
  const dados = serieMensal();
  const max = Math.max(1, ...dados.map((d) => d[1]));
  const x = (i) => m.l + (i / (dados.length - 1)) * (larg - m.l - m.r);
  const y = (v) => alt - m.b - (v / max) * (alt - m.t - m.b);

  // Grade com três linhas e rótulo em milhões de toneladas.
  for (const frac of [0, 0.5, 1]) {
    const v = max * frac;
    svg("line", { class: "grade", x1: m.l, x2: larg - m.r, y1: y(v), y2: y(v) }, el);
    svg("text", { x: m.l - 4, y: y(v) + 3, "text-anchor": "end" }, el).textContent = fmt(v / 1e6, max < 3e6 ? 1 : 0);
  }
  svg("text", { x: 0, y: 9 }, el).textContent = "mi t";

  const iAno = dados.findIndex((d) => Math.floor(d[0] / 100) === estado.ano);
  const nAno = dados.filter((d) => Math.floor(d[0] / 100) === estado.ano).length;
  if (iAno >= 0) {
    svg("rect", { class: "faixa-ano", x: x(iAno), y: m.t, width: Math.max(2, x(iAno + nAno - 1) - x(iAno)), height: alt - m.t - m.b }, el);
  }

  const caminho = (pts) => pts.map(([i, v], k) => `${k ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
  svg("path", { class: "linha", d: caminho(dados.map((d, i) => [i, d[1]])) }, el);
  if (iAno >= 0) {
    svg("path", { class: "linha-ano", d: caminho(dados.slice(iAno, iAno + nAno).map((d, k) => [iAno + k, d[1]])) }, el);
  }

  for (const a of [2006, 2010, 2015, 2020, 2025]) {
    const i = dados.findIndex((d) => d[0] === a * 100 + 1);
    if (i >= 0) svg("text", { x: x(i), y: alt - 3, "text-anchor": i === 0 ? "start" : "middle" }, el).textContent = a;
  }

  const sigla = estado.ferrovia >= 0 ? siglaFerrovia(estado.ferrovia) : null;
  for (const ev of EVENTOS) {
    if (sigla && !ev.ferrovias.includes(sigla)) continue;
    const i = dados.findIndex((d) => d[0] === ev.mes);
    if (i < 0) continue;
    svg("line", { class: "evento", x1: x(i), x2: x(i), y1: m.t - 4, y2: alt - m.b }, el);
    svg("text", { class: "evento-texto", x: x(i) - 3, y: m.t - 6, "text-anchor": "end" }, el).textContent = ev.texto;
  }

  // Mira e dica: a área inteira responde, não só a linha.
  const mira = svg("line", { class: "mira", y1: m.t, y2: alt - m.b, visibility: "hidden" }, el);
  const ponto = svg("circle", { class: "ponto", r: 4, visibility: "hidden" }, el);
  const indice = (ev) => {
    const r = el.getBoundingClientRect();
    const i = Math.round(((ev.clientX - r.left - m.l) / (larg - m.l - m.r)) * (dados.length - 1));
    return Math.max(0, Math.min(dados.length - 1, i));
  };
  el.onmousemove = (ev) => {
    const i = indice(ev);
    const [mes, tu] = dados[i];
    for (const [k, v] of [["x1", x(i)], ["x2", x(i)]]) mira.setAttribute(k, v);
    ponto.setAttribute("cx", x(i)); ponto.setAttribute("cy", y(tu));
    mira.setAttribute("visibility", "visible"); ponto.setAttribute("visibility", "visible");
    dica(`<strong>${MESES[(mes % 100) - 1]}/${Math.floor(mes / 100)}</strong><br>${toneladas(tu)}`, ev.clientX, ev.clientY);
  };
  el.onmouseleave = () => {
    mira.setAttribute("visibility", "hidden"); ponto.setAttribute("visibility", "hidden");
    esconderDica();
  };
  el.onclick = (ev) => {
    estado.ano = Math.floor(dados[indice(ev)][0] / 100);
    $("ano").value = estado.ano;
    atualizar();
  };
}

function atualizarCards() {
  const parcial = estado.ano === anoFinal() && mesesNoAno(estado.ano) < 12;
  const ate = mesesNoAno(estado.ano);
  const periodo = parcial ? `jan–${MESES[ate - 1]}/${estado.ano}` : `${estado.ano}`;
  $("rotulo-tu").textContent = `Toneladas em ${periodo}`;

  let atual, anterior = null;
  if (estado.estacao >= 0) {
    atual = totaisDaEstacao(estado.ano);
    // Os fluxos por estação vêm somados por ano: não há como cortar o ano
    // anterior nos mesmos meses do ano em andamento.
    if (!parcial && estado.ano > 2006) anterior = totaisDaEstacao(estado.ano - 1);
  } else {
    atual = totaisDoAno(estado.ano, ate);
    if (estado.ano > 2006) anterior = totaisDoAno(estado.ano - 1, ate);
  }

  $("tu").textContent = atual.tu ? toneladas(atual.tu) : "–";
  $("rotulo-variacao").textContent = parcial ? `vs. jan–${MESES[ate - 1]}/${estado.ano - 1}` : `vs. ${estado.ano - 1}`;
  const v = $("variacao");
  if (anterior && anterior.tu > 0) {
    const pct = (100 * (atual.tu - anterior.tu)) / anterior.tu;
    v.textContent = `${pct > 0 ? "+" : pct < 0 ? "−" : ""}${fmt(Math.abs(pct), Math.abs(pct) < 10 ? 1 : 0)}%`;
  } else {
    v.textContent = "–";
  }
  $("distancia").textContent = atual.tu ? `${fmt(atual.tku / atual.tu)} km` : "–";
  $("minerio").textContent = atual.tu && estado.grupo < 0 ? `${fmt((100 * atual.minerio) / atual.tu)}%` : "–";
}

function desenharComposicao() {
  const porGrupo = new Map();
  for (const f of fluxos) {
    // A composição mostra todos os grupos, com o escolhido em destaque.
    if (f[0] !== estado.ano || !passa(f, true, false)) continue;
    const g = grupoDaMercadoria[f[2]];
    porGrupo.set(g, (porGrupo.get(g) || 0) + f[5]);
  }
  const lista = [...porGrupo.entries()].sort((a, b) => b[1] - a[1]);
  const total = lista.reduce((s, [, t]) => s + t, 0);
  const max = lista.length ? lista[0][1] : 1;
  const el = $("composicao");
  el.replaceChildren();
  if (!lista.length) {
    el.innerHTML = '<p class="vazio">Sem carga neste recorte.</p>';
    return;
  }
  for (const [g, tu] of lista) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "barra-h" + (estado.grupo === g ? " ativa" : estado.grupo >= 0 ? " apagada" : "");
    b.setAttribute("role", "listitem");
    b.setAttribute("aria-pressed", estado.grupo === g);
    b.title = `${meta.grupos[g][0]}: ${toneladas(tu)}`;
    b.innerHTML = `<span class="nome">${meta.grupos[g][0]}</span>
      <span class="trilho"><span class="valor" style="display:block;width:${(100 * tu) / max}%"></span></span>
      <span class="numero">${percentual(tu / total)}</span>`;
    b.onclick = () => {
      estado.grupo = estado.grupo === g ? -1 : g;
      $("grupo").value = estado.grupo;
      atualizar();
    };
    el.appendChild(b);
  }
}

function desenharRotas() {
  const el = $("rotas");
  el.replaceChildren();
  const lista = rotas().slice(0, 8);
  if (!lista.length) {
    el.innerHTML = '<li class="vazio">Sem rotas neste recorte.</li>';
    return;
  }
  for (const r of lista) {
    const li = document.createElement("li");
    const [cr, cg, cb] = CORES[r.cat];
    li.innerHTML = `<span class="sw" style="background:rgb(${cr},${cg},${cb})"></span>
      <span class="trecho">${estacoes[r.o][0]} → ${estacoes[r.d][0]} <span>· ${fmt(r.tku / r.tu)} km</span></span>
      <span class="numero">${toneladas(r.tu)}</span>`;
    li.onmouseenter = () => { rotaEmFoco = r; desenharMapa(); };
    li.onmouseleave = () => { rotaEmFoco = null; desenharMapa(); };
    el.appendChild(li);
  }
}

function atualizarEstacao() {
  const painel = $("estacao-painel");
  painel.hidden = estado.estacao < 0;
  if (estado.estacao < 0) return;
  const i = estado.estacao;
  let emb = 0, rec = 0;
  const parceiros = new Map(), mercs = new Map();
  for (const f of selecao) {
    if (f[3] === i) emb += f[5];
    if (f[4] === i) rec += f[5];
    const outro = f[3] === i ? f[4] : f[3];
    if (outro !== i) parceiros.set(outro, (parceiros.get(outro) || 0) + f[5]);
    mercs.set(f[2], (mercs.get(f[2]) || 0) + f[5]);
  }
  const topo = (mapa, n) => [...mapa.entries()].sort((a, b) => b[1] - a[1]).slice(0, n);
  $("est-nome").textContent = nomeEstacao(i);
  $("est-resumo").innerHTML = selecao.length
    ? `Em ${estado.ano}: embarcou <strong>${toneladas(emb)}</strong> e recebeu <strong>${toneladas(rec)}</strong>.<br>
       Principais cargas: ${topo(mercs, 3).map(([m]) => meta.mercadorias[m][0]).join(", ")}.<br>
       ${parceiros.size ? `Mais ligada a: ${topo(parceiros, 3).map(([e]) => estacoes[e][0]).join(", ")}.` : ""}`
    : `Sem movimento em ${estado.ano} neste recorte.`;
}

function atualizarRecorte() {
  const partes = [estado.ferrovia >= 0 ? meta.ferrovias[estado.ferrovia][1] : "Todas as ferrovias"];
  if (estado.grupo >= 0) partes.push(meta.grupos[estado.grupo][0]);
  if (estado.estacao >= 0) partes.push(estacoes[estado.estacao][0]);
  $("recorte").textContent = partes.join(" · ");
  $("limpar").hidden = estado.grupo < 0 && estado.estacao < 0 && estado.ferrovia === padraoFerrovia();
  $("rotulo-serie").textContent = estado.estacao >= 0 ? "Toneladas por mês na ferrovia" : "Toneladas por mês";
}

function atualizarListaEstacoes() {
  const vistas = new Set();
  for (const f of fluxos) if (passa(f, false)) { vistas.add(f[3]); vistas.add(f[4]); }
  $("lista-estacoes").replaceChildren(...[...vistas].sort((a, b) => nomeEstacao(a).localeCompare(nomeEstacao(b), "pt-BR"))
    .map((i) => Object.assign(document.createElement("option"), { value: nomeEstacao(i) })));
  $("estacao").value = estado.estacao >= 0 ? nomeEstacao(estado.estacao) : "";
}

function gravarEndereco() {
  const partes = [estado.ferrovia >= 0 ? siglaFerrovia(estado.ferrovia) : "todas", estado.ano];
  history.replaceState(null, "", `#${partes.join("/")}`);
}

function atualizar({ reenquadrar = false } = {}) {
  calcularSelecao();
  atualizarRecorte();
  atualizarCards();
  desenharSerie();
  atualizarEstacao();
  desenharComposicao();
  desenharRotas();
  desenharMapa();
  gravarEndereco();
  if (reenquadrar) enquadrar();
}

function escolherEstacao(i) {
  estado.estacao = i;
  $("estacao").value = i >= 0 ? nomeEstacao(i) : "";
  atualizar({ reenquadrar: true });
}

// ---------- controles ----------

const padraoFerrovia = () => meta.ferrovias.findIndex((f) => f[0] === "MRS");

function ligarControles() {
  const fer = $("ferrovia");
  fer.append(new Option("Todas as ferrovias", -1));
  meta.ferrovias.forEach(([sigla, nome], i) => fer.append(new Option(`${nome} (${sigla})`, i)));
  fer.value = estado.ferrovia;
  fer.onchange = () => {
    estado.ferrovia = Number(fer.value);
    estado.estacao = -1;
    atualizarListaEstacoes();
    atualizar({ reenquadrar: true });
  };

  const ano = $("ano");
  for (let a = anoFinal(); a >= 2006; a--) {
    ano.append(new Option(mesesNoAno(a) < 12 ? `${a} (até ${MESES[mesesNoAno(a) - 1]})` : a, a));
  }
  ano.value = estado.ano;
  ano.onchange = () => { estado.ano = Number(ano.value); atualizar(); };

  const gru = $("grupo");
  meta.grupos.forEach(([nome], i) => gru.append(new Option(nome, i)));
  gru.onchange = () => {
    estado.grupo = Number(gru.value);
    atualizarListaEstacoes();
    atualizar();
  };

  const est = $("estacao");
  est.onchange = () => {
    const i = estacoes.findIndex((_, k) => nomeEstacao(k) === est.value);
    if (i >= 0 || est.value === "") escolherEstacao(i);
  };
  $("est-fechar").onclick = () => escolherEstacao(-1);

  $("limpar").onclick = () => {
    estado = { ...estado, ferrovia: padraoFerrovia(), grupo: -1, estacao: -1 };
    fer.value = estado.ferrovia; gru.value = -1;
    atualizarListaEstacoes();
    atualizar({ reenquadrar: true });
  };

  $("legenda").replaceChildren(...meta.categorias.map((c, i) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="sw" style="background:rgb(${CORES[i].join(",")})"></span>${c}`;
    return li;
  }));

  let espera;
  addEventListener("resize", () => { clearTimeout(espera); espera = setTimeout(desenharSerie, 150); });
}

function lerEndereco() {
  const [sigla, ano] = location.hash.slice(1).split("/");
  if (sigla === "todas") estado.ferrovia = -1;
  else if (sigla) {
    const i = meta.ferrovias.findIndex((f) => f[0] === sigla.toUpperCase());
    if (i >= 0) estado.ferrovia = i;
  }
  if (Number(ano) >= 2006 && Number(ano) <= anoFinal()) estado.ano = Number(ano);
}

async function iniciar() {
  [meta, estacoes, fluxos, serie] = await Promise.all(
    ["meta", "estacoes", "fluxos", "serie"].map((n) => json(`data/${n}.json`)),
  );
  grupoDaMercadoria = meta.mercadorias.map((m) => m[1]);
  categoriaDoGrupo = meta.grupos.map((g) => g[1]);

  // Abre no último ano completo, na MRS.
  estado.ano = mesesNoAno(anoFinal()) === 12 ? anoFinal() : anoFinal() - 1;
  estado.ferrovia = padraoFerrovia();
  lerEndereco();

  const [a, m] = meta.ultimo_mes.split("-");
  $("atualizado").textContent = `dados até ${MESES[Number(m) - 1]}/${a}`;

  mapa = new maplibregl.Map({
    container: "mapa",
    style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
    center: [-47, -16],
    zoom: 3.6,
    attributionControl: { compact: true },
  });
  overlay = new deck.MapboxOverlay({ layers: [] });
  mapa.addControl(overlay);
  mapa.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");

  ligarControles();
  atualizarListaEstacoes();
  mapa.on("load", () => atualizar({ reenquadrar: true }));
}

iniciar().catch((erro) => {
  $("atualizado").textContent = "falha ao carregar os dados";
  console.error(erro);
});
