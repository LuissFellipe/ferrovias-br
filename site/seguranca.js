// Página de acidentes. Como na de carga, tudo é calculado no navegador: um
// acidente por linha em acidentes.json e, em seguranca_meta.json, as listas
// que os índices apontam e a tabela anual por ferrovia com o TKU.
//
// acidente: [ano, ferrovia, natureza, grave, óbitos, feridos, passagem em nível,
//            local, município, suicídio registrado]
// anual:    [ferrovia, ano, acidentes, graves, óbitos, TKU em milhões, índice oficial]

const CORES = [[217, 89, 38], [57, 135, 229], [25, 158, 112], [138, 138, 146]];
const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const ANO_INICIAL = 2004;
// Até 2009 o registro só tem os graves e quase nenhum óbito; 2010 é transição.
const ANO_COMPLETO = 2011;
// A causa contributiva, onde aparece o suicídio, só existe desde dez/2020.
const ANO_CAUSA_CONTRIBUTIVA = 2021;

let meta, acidentes;
let mapa, overlay;
let estado = { ferrovia: -1, de: ANO_COMPLETO, ate: 0, natureza: -1, municipio: -1 };
let selecao = [];

const $ = (id) => document.getElementById(id);

async function json(caminho) {
  const resp = await fetch(caminho);
  if (!resp.ok) throw new Error(`${caminho}: ${resp.status}`);
  return resp.json();
}

const fmt = (n, casas = 0) => n.toLocaleString("pt-BR", { maximumFractionDigits: casas, minimumFractionDigits: casas });
const percentual = (f) => `${fmt(100 * f, f < 0.1 ? 1 : 0)}%`;
const nomeMunicipio = (i) => `${meta.municipios[i][0]} (${meta.municipios[i][1]})`;

// ---------- recortes ----------

const ultimoDia = () => meta.ultimo_dia;
const anoFinal = () => Number(ultimoDia().slice(0, 4));
const mesFinal = () => Number(ultimoDia().slice(5, 7));
const ultimoAnoCompleto = () => (mesFinal() === 12 ? anoFinal() : anoFinal() - 1);
const periodoPadrao = () => ({ de: ANO_COMPLETO, ate: ultimoAnoCompleto() });

function passa(a, { periodo = true, natureza = true, municipio = true } = {}) {
  if (estado.ferrovia >= 0 && a[1] !== estado.ferrovia) return false;
  if (periodo && (a[0] < estado.de || a[0] > estado.ate)) return false;
  if (natureza && estado.natureza >= 0 && a[2] !== estado.natureza) return false;
  if (municipio && estado.municipio >= 0 && a[8] !== estado.municipio) return false;
  return true;
}

function textoPeriodo() {
  if (estado.de !== estado.ate) return `${estado.de}–${estado.ate}`;
  return estado.ate === anoFinal() && mesFinal() < 12 ? `jan–${MESES[mesFinal() - 1]}/${estado.ate}` : `${estado.ate}`;
}

// ---------- mapa ----------

function porLocal() {
  const locais = new Map();
  for (const a of selecao) {
    if (a[7] < 0) continue;
    let l = locais.get(a[7]);
    if (!l) locais.set(a[7], (l = { i: a[7], n: 0, obitos: 0, porNat: [0, 0, 0, 0], municipios: new Map() }));
    l.n++; l.obitos += a[4]; l.porNat[a[2]]++;
    if (a[8] >= 0) l.municipios.set(a[8], (l.municipios.get(a[8]) || 0) + 1);
  }
  const lista = [...locais.values()];
  for (const l of lista) l.nat = l.porNat.indexOf(Math.max(...l.porNat));
  return lista.sort((a, b) => a.n - b.n);
}

const posicao = (i) => [meta.locais[i][2] / 1e4, meta.locais[i][1] / 1e4];

function desenharMapa() {
  const lista = porLocal();
  const max = lista.length ? lista[lista.length - 1].n : 1;
  overlay.setProps({
    layers: [
      new deck.ScatterplotLayer({
        id: "acidentes",
        data: lista,
        getPosition: (l) => posicao(l.i),
        getRadius: (l) => 2.5 + 16 * Math.sqrt(l.n / max),
        radiusUnits: "pixels",
        getFillColor: (l) => [...CORES[l.nat], 190],
        getLineColor: [20, 21, 27, 255],
        lineWidthUnits: "pixels",
        getLineWidth: 1,
        stroked: true,
        pickable: true,
        autoHighlight: true,
        highlightColor: [255, 255, 255, 90],
        onHover: ({ object, x, y }) => (object ? dica(textoLocal(object), x, y) : esconderDica()),
      }),
    ],
  });
}

function textoLocal(l) {
  const nats = l.porNat.map((n, k) => [k, n]).filter(([, n]) => n).sort((a, b) => b[1] - a[1])
    .map(([k, n]) => `${meta.naturezas[k]}: ${fmt(n)}`).join("<br>");
  const muns = [...l.municipios.entries()].sort((a, b) => b[1] - a[1]).slice(0, 2).map(([m]) => nomeMunicipio(m)).join(", ");
  return `<strong>${meta.locais[l.i][0]}</strong><br>
    ${fmt(l.n)} ${l.n === 1 ? "acidente" : "acidentes"} · ${fmt(l.obitos)} ${l.obitos === 1 ? "óbito" : "óbitos"} em ${textoPeriodo()}<br>
    <span class="t2">${nats}${muns ? `<br>${muns}` : ""}</span>`;
}

function dica(html, x, y) {
  const t = $("tooltip");
  t.innerHTML = html;
  t.hidden = false;
  t.style.left = `${Math.min(x + 14, innerWidth - t.offsetWidth - 8)}px`;
  t.style.top = `${Math.min(y + 14, innerHeight - t.offsetHeight - 8)}px`;
}
const esconderDica = () => ($("tooltip").hidden = true);

function margens() {
  if (innerWidth <= 720) return { top: 40, bottom: innerHeight * 0.52, left: 30, right: 30 };
  return { top: 50, bottom: 50, left: 410, right: 50 };
}

function enquadrar() {
  const pts = selecao.filter((a) => a[7] >= 0).map((a) => posicao(a[7]));
  if (!pts.length) return;
  const lons = pts.map((p) => p[0]), lats = pts.map((p) => p[1]);
  mapa.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]],
    { padding: margens(), maxZoom: 11, duration: 800 });
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
  const m = { t: 8, r: 2, b: 16, l: 30 };
  const anos = [];
  for (let a = ANO_INICIAL; a <= anoFinal(); a++) anos.push({ ano: a, n: 0, obitos: 0 });
  for (const a of acidentes) {
    if (!passa(a, { periodo: false })) continue;
    const d = anos[a[0] - ANO_INICIAL];
    d.n++; d.obitos += a[4];
  }
  const max = Math.max(1, ...anos.map((d) => d.n));
  const passo = (larg - m.l - m.r) / anos.length;
  const y = (v) => alt - m.b - (v / max) * (alt - m.t - m.b);

  for (const frac of [0, 0.5, 1]) {
    const v = Math.round(max * frac);
    svg("line", { class: "grade", x1: m.l, x2: larg - m.r, y1: y(v), y2: y(v) }, el);
    svg("text", { x: m.l - 4, y: y(v) + 3, "text-anchor": "end" }, el).textContent = fmt(v);
  }

  anos.forEach((d, k) => {
    const dentro = d.ano >= estado.de && d.ano <= estado.ate;
    const classe = d.ano < ANO_COMPLETO ? "barra incompleta" : dentro ? "barra ativa" : "barra";
    svg("rect", {
      class: classe,
      x: m.l + k * passo + passo * 0.15,
      y: y(d.n),
      width: passo * 0.7,
      height: Math.max(0, alt - m.b - y(d.n)),
    }, el);
    if (d.ano % 5 === 0) {
      svg("text", { x: m.l + k * passo + passo / 2, y: alt - 3, "text-anchor": "middle" }, el).textContent = d.ano;
    }
  });

  const indice = (ev) => {
    const r = el.getBoundingClientRect();
    return Math.max(0, Math.min(anos.length - 1, Math.floor((ev.clientX - r.left - m.l) / passo)));
  };
  el.onmousemove = (ev) => {
    const d = anos[indice(ev)];
    const parcial = d.ano === anoFinal() && mesFinal() < 12 ? ` (até ${MESES[mesFinal() - 1]})` : "";
    const aviso = d.ano < ANO_COMPLETO ? '<br><span class="t2">registro incompleto: só graves, sem óbitos</span>' : "";
    dica(`<strong>${d.ano}${parcial}</strong><br>${fmt(d.n)} acidentes · ${fmt(d.obitos)} óbitos${aviso}`, ev.clientX, ev.clientY);
  };
  el.onmouseleave = esconderDica;
  el.onclick = (ev) => {
    const ano = anos[indice(ev)].ano;
    const padrao = periodoPadrao();
    // Clicar de novo no ano escolhido volta ao período inteiro.
    Object.assign(estado, estado.de === ano && estado.ate === ano ? padrao : { de: ano, ate: ano });
    $("periodo").value = `${estado.de}-${estado.ate}`;
    atualizar();
  };
}

function atualizarCards() {
  let n = 0, obitos = 0, graves = 0, pn = 0;
  for (const a of selecao) { n++; obitos += a[4]; graves += a[3]; pn += a[6]; }
  $("acidentes").textContent = fmt(n);
  $("obitos").textContent = fmt(obitos);
  $("graves").textContent = n ? percentual(graves / n) : "–";
  $("pn").textContent = n ? percentual(pn / n) : "–";
}

function barra(nome, valor, max, numero, { ativa = false, apagada = false, titulo = "", onclick = null } = {}) {
  const b = document.createElement(onclick ? "button" : "div");
  if (onclick) { b.type = "button"; b.onclick = onclick; b.setAttribute("aria-pressed", ativa); }
  b.className = "barra-h" + (ativa ? " ativa" : apagada ? " apagada" : "");
  b.setAttribute("role", "listitem");
  b.title = titulo;
  b.innerHTML = `<span class="nome">${nome}</span>
    <span class="trilho"><span class="valor" style="display:block;width:${max ? (100 * valor) / max : 0}%"></span></span>
    <span class="numero">${numero}</span>`;
  return b;
}

function desenharNaturezas() {
  const cont = [0, 0, 0, 0], obitos = [0, 0, 0, 0];
  for (const a of acidentes) {
    if (!passa(a, { natureza: false })) continue;
    cont[a[2]]++; obitos[a[2]] += a[4];
  }
  const total = cont.reduce((s, n) => s + n, 0);
  const el = $("naturezas");
  el.replaceChildren();
  if (!total) { el.innerHTML = '<p class="vazio">Sem acidentes neste recorte.</p>'; return; }
  const max = Math.max(...cont);
  meta.naturezas.map((nome, k) => [nome, k]).sort((a, b) => cont[b[1]] - cont[a[1]]).forEach(([nome, k]) => {
    if (!cont[k]) return;
    el.appendChild(barra(nome, cont[k], max, percentual(cont[k] / total), {
      ativa: estado.natureza === k,
      apagada: estado.natureza >= 0 && estado.natureza !== k,
      titulo: `${nome}: ${fmt(cont[k])} acidentes, ${fmt(obitos[k])} óbitos`,
      onclick: () => { estado.natureza = estado.natureza === k ? -1 : k; atualizar(); },
    }));
  });
}

// Graves por bilhão de TKU no período, só nos anos de registro completo.
function desenharComparacao() {
  const de = Math.max(estado.de, ANO_COMPLETO), ate = estado.ate;
  const el = $("comparacao");
  el.replaceChildren();
  $("rotulo-comparacao").textContent = de > ate ? "sem anos completos" : de === ate ? `${de}` : `${de}–${ate}`;
  if (de > ate) { el.innerHTML = '<p class="vazio">Escolha um período a partir de 2011.</p>'; return; }
  const soma = new Map();
  for (const [f, ano, , graves, , tku] of meta.anual) {
    if (ano < de || ano > ate || !tku) continue;
    let s = soma.get(f);
    if (!s) soma.set(f, (s = { graves: 0, tku: 0 }));
    s.graves += graves; s.tku += tku;
  }
  // Menos de 1 bilhão de TKU por ano dá taxas que um acidente a mais dobra.
  const minimo = 1000 * (ate - de + 1);
  const lista = [...soma.entries()].filter(([, s]) => s.tku >= minimo)
    .map(([f, s]) => [f, (1000 * s.graves) / s.tku]).sort((a, b) => a[1] - b[1]);
  const max = Math.max(...lista.map(([, v]) => v));
  for (const [f, v] of lista) {
    el.appendChild(barra(meta.ferrovias[f][0], v, max, fmt(v, v < 10 ? 2 : 1), {
      ativa: f === estado.ferrovia,
      apagada: estado.ferrovia >= 0 && f !== estado.ferrovia,
      titulo: meta.ferrovias[f][1],
    }));
  }
}

function desenharMunicipios() {
  const cont = new Map();
  // A lista ignora o município escolhido, para ele continuar nela em destaque.
  for (const a of acidentes) {
    if (a[8] < 0 || !passa(a, { municipio: false })) continue;
    let c = cont.get(a[8]);
    if (!c) cont.set(a[8], (c = { n: 0, obitos: 0 }));
    c.n++; c.obitos += a[4];
  }
  const el = $("municipios");
  el.replaceChildren();
  const lista = [...cont.entries()].sort((a, b) => b[1].n - a[1].n).slice(0, 8);
  if (!lista.length) { el.innerHTML = '<li class="vazio">Sem acidentes neste recorte.</li>'; return; }
  for (const [m, c] of lista) {
    const li = document.createElement("li");
    li.className = "clicavel" + (m === estado.municipio ? " ativa" : "");
    li.tabIndex = 0;
    li.innerHTML = `<span class="sw" style="background:var(--texto-2)"></span>
      <span class="trecho">${nomeMunicipio(m)} <span>· ${fmt(c.obitos)} ${c.obitos === 1 ? "óbito" : "óbitos"}</span></span>
      <span class="numero">${fmt(c.n)}</span>`;
    const escolher = () => escolherMunicipio(m === estado.municipio ? -1 : m);
    li.onclick = escolher;
    li.onkeydown = (ev) => (ev.key === "Enter" || ev.key === " ") && (ev.preventDefault(), escolher());
    el.appendChild(li);
  }
}

// O registro de suicídio só existe desde dez/2020 e só nos atropelamentos.
function atualizarNotaCvv() {
  let fatais = 0, suicidios = 0;
  for (const a of acidentes) {
    if (a[0] < ANO_CAUSA_CONTRIBUTIVA || a[2] !== 0 || !a[4] || !passa(a, { natureza: false })) continue;
    fatais++; suicidios += a[9];
  }
  const nota = $("nota-cvv");
  nota.hidden = fatais < 5 || !suicidios;
  if (nota.hidden) return;
  const de = Math.max(estado.de, ANO_CAUSA_CONTRIBUTIVA);
  $("texto-cvv").textContent = `De ${de === estado.ate ? de : `${de} a ${estado.ate}`}, ${fmt(suicidios)} dos ${fmt(fatais)} atropelamentos com morte neste recorte foram registrados pela concessionária como suicídio ou tentativa.`;
}

function atualizarRecorte() {
  const partes = [estado.ferrovia >= 0 ? meta.ferrovias[estado.ferrovia][1] : "Todas as ferrovias", textoPeriodo()];
  if (estado.natureza >= 0) partes.push(meta.naturezas[estado.natureza]);
  if (estado.municipio >= 0) partes.push(nomeMunicipio(estado.municipio));
  $("recorte").textContent = partes.join(" · ");
  const p = periodoPadrao();
  $("limpar").hidden = estado.natureza < 0 && estado.municipio < 0 && estado.de === p.de && estado.ate === p.ate
    && estado.ferrovia === padraoFerrovia();
}

function atualizarListaMunicipios() {
  const vistos = new Set(acidentes.filter((a) => a[8] >= 0 && passa(a, { periodo: false, natureza: false, municipio: false })).map((a) => a[8]));
  $("lista-municipios").replaceChildren(...[...vistos].sort((a, b) => nomeMunicipio(a).localeCompare(nomeMunicipio(b), "pt-BR"))
    .map((i) => Object.assign(document.createElement("option"), { value: nomeMunicipio(i) })));
  $("municipio").value = estado.municipio >= 0 ? nomeMunicipio(estado.municipio) : "";
}

function gravarEndereco() {
  const sigla = estado.ferrovia >= 0 ? meta.ferrovias[estado.ferrovia][0] : "todas";
  const periodo = estado.de === estado.ate ? estado.de : `${estado.de}-${estado.ate}`;
  history.replaceState(null, "", `#${sigla}/${periodo}`);
}

function atualizar({ reenquadrar = false } = {}) {
  selecao = acidentes.filter((a) => passa(a));
  atualizarRecorte();
  atualizarCards();
  desenharSerie();
  desenharNaturezas();
  desenharComparacao();
  desenharMunicipios();
  atualizarNotaCvv();
  desenharMapa();
  gravarEndereco();
  if (reenquadrar) enquadrar();
}

function escolherMunicipio(i) {
  estado.municipio = i;
  $("municipio").value = i >= 0 ? nomeMunicipio(i) : "";
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
    estado.municipio = -1;
    atualizarListaMunicipios();
    atualizar({ reenquadrar: true });
  };

  const per = $("periodo");
  const p = periodoPadrao();
  per.append(new Option(`${p.de}–${p.ate}`, `${p.de}-${p.ate}`));
  for (let a = anoFinal(); a >= ANO_INICIAL; a--) {
    const sufixo = a === anoFinal() && mesFinal() < 12 ? ` (até ${MESES[mesFinal() - 1]})` : a < ANO_COMPLETO ? " · incompleto" : "";
    per.append(new Option(`${a}${sufixo}`, `${a}-${a}`));
  }
  per.value = `${estado.de}-${estado.ate}`;
  per.onchange = () => {
    [estado.de, estado.ate] = per.value.split("-").map(Number);
    atualizar();
  };

  const mun = $("municipio");
  mun.onchange = () => {
    const i = meta.municipios.findIndex((_, k) => nomeMunicipio(k) === mun.value);
    if (i >= 0 || mun.value === "") escolherMunicipio(i);
  };

  $("limpar").onclick = () => {
    estado = { ...estado, ...periodoPadrao(), ferrovia: padraoFerrovia(), natureza: -1, municipio: -1 };
    fer.value = estado.ferrovia;
    per.value = `${estado.de}-${estado.ate}`;
    atualizarListaMunicipios();
    atualizar({ reenquadrar: true });
  };

  $("legenda").replaceChildren(...meta.naturezas.map((n, i) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="sw ponto" style="background:rgb(${CORES[i].join(",")})"></span>${n}`;
    return li;
  }));

  let espera;
  addEventListener("resize", () => { clearTimeout(espera); espera = setTimeout(desenharSerie, 150); });
}

function lerEndereco() {
  const [sigla, periodo] = location.hash.slice(1).split("/");
  if (sigla === "todas") estado.ferrovia = -1;
  else if (sigla) {
    const i = meta.ferrovias.findIndex((f) => f[0] === sigla.toUpperCase());
    if (i >= 0) estado.ferrovia = i;
  }
  const [de, ate = de] = (periodo || "").split("-").map(Number);
  if (de >= ANO_INICIAL && ate <= anoFinal() && de <= ate) {
    // O seletor só tem o período padrão e os anos isolados.
    const p = periodoPadrao();
    if (de === ate || (de === p.de && ate === p.ate)) Object.assign(estado, { de, ate });
  }
}

async function iniciar() {
  [meta, acidentes] = await Promise.all([json("data/seguranca_meta.json"), json("data/acidentes.json")]);

  Object.assign(estado, periodoPadrao(), { ferrovia: padraoFerrovia() });
  lerEndereco();

  $("atualizado").textContent = `dados até ${MESES[mesFinal() - 1]}/${anoFinal()}`;

  mapa = new maplibregl.Map({
    container: "mapa",
    style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
    center: [-45, -21],
    zoom: 5,
    attributionControl: { compact: true },
  });
  overlay = new deck.MapboxOverlay({ layers: [] });
  mapa.addControl(overlay);
  mapa.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");

  ligarControles();
  atualizarListaMunicipios();
  mapa.on("load", () => atualizar({ reenquadrar: true }));
}

iniciar().catch((erro) => {
  $("atualizado").textContent = "falha ao carregar os dados";
  console.error(erro);
});
