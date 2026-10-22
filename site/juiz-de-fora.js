// Página de Juiz de Fora. O ranking já vem calculado em data/jf.json
// (export_jf.py); aqui só se desenha.
//
// atropelamento: [lon·1e5, lat·1e5, ano, em passagem em nível, com óbito, trecho]

const LARANJA = [217, 89, 38];
const AZUL = [57, 135, 229];
const VERDE = [25, 158, 112];
const CINZA = [138, 138, 146];
const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const NO_RANKING = 8;

let dados, mapa, overlay;
let selecionado = null;

const $ = (id) => document.getElementById(id);
const fmt = (n, casas = 0) => n.toLocaleString("pt-BR", { maximumFractionDigits: casas, minimumFractionDigits: casas });
const reais = (n) => (n >= 1e6 ? `R$ ${fmt(n / 1e6, 1)} milhão` : `R$ ${fmt(Math.round(n / 1000))} mil`);
const porKm = (km) => dados.trechos.find((t) => t.km === km);
const ordenados = () => [...dados.trechos].sort((a, b) => a.posicao - b.posicao);
const ruas = (t) => (t.ruas.length ? t.ruas.join(", ") : "sem rua com nome cruzando no OSM");

// ---------- tooltip ----------

function mostrarTooltip(x, y, html) {
  const tip = $("tooltip");
  tip.innerHTML = html;
  tip.hidden = false;
  const largura = tip.offsetWidth;
  tip.style.left = `${Math.min(x + 14, window.innerWidth - largura - 8)}px`;
  tip.style.top = `${y + 14}px`;
}
const esconderTooltip = () => ($("tooltip").hidden = true);

function textoTrecho(t) {
  return `<strong>km ${t.km}</strong> <span class="t2">${ruas(t)}</span><br>
    ${t.atropelamentos} atropelamentos, ${t.obitos} óbitos<br>
    <span class="t2">esperado ${fmt(t.esperado, 1)} · estimado ${fmt(t.eb, 1)} (${fmt(t.eb_ic90[0], 1)}–${fmt(t.eb_ic90[1], 1)})</span>`;
}

// ---------- mapa ----------

function camadas() {
  const maxExcesso = Math.max(...dados.trechos.map((t) => t.excesso));
  const corTrecho = (t) => {
    if (t.excesso <= 0.5) return [...CINZA, 150];
    return [...LARANJA, Math.round(110 + 145 * (t.excesso / maxExcesso))];
  };
  return [
    new deck.PathLayer({
      id: "selecao",
      data: selecionado ? [porKm(selecionado)] : [],
      getPath: (t) => t.linha,
      getColor: [236, 235, 231],
      getWidth: 14,
      widthUnits: "pixels",
      capRounded: true,
    }),
    new deck.PathLayer({
      id: "trechos",
      data: dados.trechos,
      getPath: (t) => t.linha,
      getColor: corTrecho,
      getWidth: (t) => (t.excesso > 0.5 ? 9 : 5),
      widthUnits: "pixels",
      capRounded: true,
      pickable: true,
      onHover: ({ object, x, y }) => (object ? mostrarTooltip(x, y, textoTrecho(object)) : esconderTooltip()),
      onClick: ({ object }) => object && selecionar(object.km),
      updateTriggers: { getColor: selecionado },
    }),
    new deck.ScatterplotLayer({
      id: "atropelamentos",
      data: dados.atropelamentos,
      getPosition: (a) => [a[0] / 1e5, a[1] / 1e5],
      getFillColor: (a) => (a[3] ? AZUL : VERDE),
      getLineColor: [14, 15, 19],
      lineWidthMinPixels: 1,
      stroked: true,
      radiusUnits: "pixels",
      getRadius: 3,
      pickable: true,
      onHover: ({ object, x, y }) =>
        object
          ? mostrarTooltip(x, y, `<strong>${object[2]}</strong> · km ${object[5]}<br>
              <span class="t2">${object[3] ? "em passagem em nível" : "fora da passagem em nível"}${object[4] ? " · com óbito" : ""}</span>`)
          : esconderTooltip(),
    }),
    new deck.TextLayer({
      id: "rotulos",
      data: ordenados().slice(0, NO_RANKING),
      getPosition: (t) => t.linha[Math.floor(t.linha.length / 2)],
      getText: (t) => `km ${t.km}`,
      getSize: 12,
      getColor: [236, 235, 231],
      background: true,
      getBackgroundColor: [20, 21, 27, 230],
      backgroundPadding: [4, 2],
      getPixelOffset: [0, -16],
      fontFamily: "Inter, system-ui, sans-serif",
      fontWeight: 600,
    }),
  ];
}

function desenharMapa() {
  overlay.setProps({ layers: camadas() });
}

function enquadrar(trechos) {
  const pts = trechos.flatMap((t) => t.linha);
  const lons = pts.map((p) => p[0]);
  const lats = pts.map((p) => p[1]);
  const estreito = window.innerWidth <= 720;
  mapa.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], {
    padding: estreito ? { top: 40, bottom: window.innerHeight * 0.5 + 30, left: 30, right: 30 } : { top: 60, bottom: 60, left: 420, right: 60 },
    maxZoom: 15,
    duration: 600,
  });
}

// ---------- ranking ----------

function desenharRanking() {
  const svg = $("ranking");
  const linhas = ordenados().slice(0, NO_RANKING);
  const L = svg.clientWidth || 320;
  const altura = 26;
  const esq = 54;
  const dir = 44;
  svg.setAttribute("height", linhas.length * altura + 18);
  const max = Math.max(...linhas.map((t) => Math.max(t.eb_ic90[1], t.esperado))) * 1.05;
  const x = (v) => esq + (v / max) * (L - esq - dir);
  let html = "";
  for (const v of [0, 10, 20, 30, 40].filter((v) => v <= max)) {
    html += `<line class="grade" x1="${x(v)}" x2="${x(v)}" y1="0" y2="${linhas.length * altura}"/>
      <text x="${x(v)}" y="${linhas.length * altura + 13}" text-anchor="middle">${v}</text>`;
  }
  linhas.forEach((t, i) => {
    const y = i * altura + altura / 2;
    const ativo = t.km === selecionado ? " ativa" : "";
    html += `<g class="linha-ranking${ativo}" data-km="${t.km}" tabindex="0" role="button" aria-label="km ${t.km}">
      <rect class="alvo" x="0" y="${i * altura}" width="${L}" height="${altura}"/>
      <text class="nome" x="0" y="${y + 4}">km ${t.km}</text>
      <line class="intervalo" x1="${x(t.eb_ic90[0])}" x2="${x(t.eb_ic90[1])}" y1="${y}" y2="${y}"/>
      <line class="esperado" x1="${x(t.esperado)}" x2="${x(t.esperado)}" y1="${y - 7}" y2="${y + 7}"/>
      <circle class="estimado" cx="${x(t.eb)}" cy="${y}" r="5"/>
      <text class="valor" x="${L}" y="${y + 4}" text-anchor="end">${t.excesso > 0 ? "+" : ""}${fmt(t.excesso, 1)}</text>
    </g>`;
  });
  svg.innerHTML = html;
  for (const g of svg.querySelectorAll(".linha-ranking")) {
    const t = porKm(Number(g.dataset.km));
    g.addEventListener("click", () => selecionar(t.km));
    g.addEventListener("keydown", (e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), selecionar(t.km)));
    g.addEventListener("mousemove", (e) => mostrarTooltip(e.clientX, e.clientY, textoTrecho(t)));
    g.addEventListener("mouseleave", esconderTooltip);
  }
  const contagem = dados.top_contagem.map((k) => `km ${k}`).join(", ");
  $("comparacao-contagem").textContent =
    `Pela contagem bruta a ordem seria ${contagem}: o km 276 cai porque o movimento em volta dele explica quase todos os casos.`;
}

// ---------- detalhe ----------

function intervencao(t) {
  if (!t.perfil) return "";
  const pn = t.perfil.em_pn;
  if (pn >= 0.5) {
    return `<strong>${fmt(100 * pn)}% dos atropelamentos foram em passagem em nível.</strong> A intervenção é na passagem: travessia de pedestre separada, sinalização sonora e luminosa, cancela. Ruas que cruzam a linha no trecho: ${ruas(t)}.`;
  }
  return `<strong>${fmt(100 * (1 - pn))}% dos atropelamentos foram fora de passagem em nível</strong>, onde as pessoas atravessam onde não há travessia. A intervenção é vedação, junto com uma travessia segura no caminho que as pessoas já fazem: sem ela, a grade é aberta de novo.`;
}

function desenharHoras(t) {
  const bloco = $("d-horas-bloco");
  bloco.hidden = !t.perfil;
  if (!t.perfil) return;
  const svg = $("d-horas");
  const L = svg.clientWidth || 320;
  const A = 90;
  const h = t.perfil.horas;
  const max = Math.max(...h, 1);
  const largura = (L - 7 * 2) / 8;
  let html = "";
  h.forEach((n, i) => {
    const alt = (n / max) * (A - 30);
    const x = i * (largura + 2);
    html += `<rect class="barra" x="${x}" y="${A - 16 - alt}" width="${largura}" height="${alt}" rx="2"><title>${i * 3}h–${i * 3 + 3}h: ${n}</title></rect>
      <text x="${x + largura / 2}" y="${A - 18 - alt}" text-anchor="middle">${n || ""}</text>
      <text x="${x + largura / 2}" y="${A - 3}" text-anchor="middle">${i * 3}h</text>`;
  });
  svg.innerHTML = html;
}

function selecionar(km) {
  selecionado = selecionado === km ? null : km;
  location.hash = selecionado ? `km=${selecionado}` : "";
  const t = selecionado && porKm(selecionado);
  $("detalhe").hidden = !t;
  if (t) {
    $("d-titulo").textContent = `km ${t.km} · ${t.posicao}º no ranking`;
    $("d-resumo").innerHTML = `<strong>${t.atropelamentos} atropelamentos e ${t.obitos} óbitos</strong> em ${dados.anos} anos, contra
      <strong>${fmt(t.esperado, 1)}</strong> esperados para o movimento em volta. Estimado: ${fmt(t.eb, 1)}
      (90%: ${fmt(t.eb_ic90[0], 1)} a ${fmt(t.eb_ic90[1], 1)}); chance de estar acima do esperado: ${fmt(100 * t.p_acima)}%.`
      + (t.excesso > 0 ? ` O excesso equivale a ${fmt(t.obitos_evitaveis_ano, 2)} óbito por ano, ou cerca de ${reais(t.valor_social_ano_rs)} por ano em custo social.` : "");
    const escolas = t.escolas_perto.map(([nome, rede, d]) => `${nome.toLowerCase()} (${rede.toLowerCase()}, ${d} m)`).join("; ");
    $("d-entorno").innerHTML = `<strong>Em volta (500 m):</strong> ${fmt(t.moradores)} moradores (${fmt(t.moradores_lados[0])} de um lado,
      ${fmt(t.moradores_lados[1])} do outro), ${fmt(t.comercio)} endereços de comércio e serviço, ${t.escolas} escolas.`
      + (escolas ? ` Mais perto: ${escolas}.` : "")
      + ` Ruas que cruzam a linha no trecho: ${ruas(t)}.`;
    $("d-intervencao").innerHTML = intervencao(t);
    desenharHoras(t);
  }
  desenharRanking();
  desenharMapa();
  if (t) enquadrar([t]);
}

// ---------- texto ----------

function preencherTextos() {
  const a = dados.atropelamentos;
  const top3 = ordenados().slice(0, 3);
  const excesso = top3.reduce((s, t) => s + Math.max(t.excesso, 0), 0);
  const valor = top3.reduce((s, t) => s + t.valor_social_ano_rs, 0);
  $("c-atrop").textContent = fmt(a.length);
  $("c-obitos").textContent = fmt(dados.trechos.reduce((s, t) => s + t.obitos, 0));
  $("c-pn").textContent = `${fmt((100 * a.filter((x) => x[3]).length) / a.length)}%`;
  $("c-excesso").textContent = `${fmt(excesso / dados.anos, 1)}/ano`;

  const rob = dados.robustez;
  const vezes = (k) => rob.top3[String(k)] || 0;
  $("recomendacoes").innerHTML = top3.map((t) => {
    const pn = t.perfil ? t.perfil.em_pn : 0;
    const acao = pn >= 0.5 ? `tratar a passagem em nível (ruas que cruzam a linha no trecho: ${ruas(t)})` : `vedar e abrir travessia segura (ruas no trecho: ${ruas(t)})`;
    return `<li><button type="button" class="link" data-km="${t.km}">km ${t.km}</button>: ${acao}.
      ${t.atropelamentos} casos contra ${fmt(t.esperado, 1)} esperados; no top 3 em ${vezes(t.km)} de ${rob.sorteios} sorteios com ${rob.erro_m} m de erro de posição.</li>`;
  }).join("");
  $("total-recomendacoes").textContent = `Os três somam um excesso de ${fmt(excesso / dados.anos, 1)} atropelamento por ano, cerca de ${reais(valor)} por ano em custo social. ` +
    "É o mínimo que se ganha levando cada trecho à média; a vedação pode ganhar mais.";
  for (const b of $("recomendacoes").querySelectorAll("button")) b.addEventListener("click", () => selecionar(Number(b.dataset.km)));

  const ad = dados.antes_depois;
  $("antes-depois").textContent =
    `A passarela da Estação Central (km ${ad.trecho_km}) foi restaurada de ago/2021 a fev/2022. Contra o resto de JF, o trecho teve ` +
    `${fmt(ad.razao, 2)} vez a variação dos atropelamentos depois (2022–2025) em relação a antes (2011–2020), com intervalo de 95% de ` +
    `${fmt(ad.ic95[0], 2)} a ${fmt(ad.ic95[1], 2)}: com tão poucos casos, não dá para dizer se a passarela mudou alguma coisa.`;
}

// ---------- início ----------

async function iniciar() {
  const resp = await fetch("data/jf.json");
  if (!resp.ok) throw new Error(`data/jf.json: ${resp.status}`);
  dados = await resp.json();
  const [ano, mes] = dados.ultimo_dia.split("-").map(Number);
  $("atualizado").textContent = `RAAF até ${MESES[mes - 1]}/${ano}`;

  mapa = new maplibregl.Map({
    container: "mapa",
    style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
    center: [-43.37, -21.72],
    zoom: 11,
    attributionControl: { compact: true },
  });
  overlay = new deck.MapboxOverlay({ layers: [] });
  mapa.addControl(overlay);
  mapa.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");

  preencherTextos();
  desenharRanking();
  $("d-fechar").addEventListener("click", () => selecionar(selecionado));
  window.addEventListener("resize", () => {
    desenharRanking();
    if (selecionado) desenharHoras(porKm(selecionado));
  });

  mapa.on("load", () => {
    desenharMapa();
    const pedido = Number((location.hash.match(/km=(\d+)/) || [])[1]);
    if (pedido && porKm(pedido)) selecionar(pedido);
    else enquadrar(ordenados().slice(0, NO_RANKING));
  });
}

iniciar().catch((erro) => {
  $("atualizado").textContent = "falha ao carregar os dados";
  console.error(erro);
});
