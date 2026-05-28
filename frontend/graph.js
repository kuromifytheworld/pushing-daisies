/* Pushing Daisies — D3.js Force-Directed Character Network */

const API = (window.API_BASE || "http://localhost:8000") + "/api";

// ── State ────────────────────────────────────────────────────────────────────
const state = {
  season:       null,
  episode:      null,
  relTypes:     new Set(["DIALOGUE_WITH", "CO_APPEARS"]),
  minWeight:    2,
  allData:      { characters: [], relationships: [] },
  episodes:     [],
  pathMode:     false,
  pathFrom:     null,
  pathTo:       null,
  maxPagerank:  1,
};

// ── D3 setup ─────────────────────────────────────────────────────────────────
const container = document.getElementById("graph-container");
const W = () => container.clientWidth;
const H = () => container.clientHeight;

const svg = d3.select("#graph-svg");
const g   = svg.append("g").attr("class", "zoom-group");

svg.call(
  d3.zoom()
    .scaleExtent([0.1, 4])
    .on("zoom", (e) => g.attr("transform", e.transform))
);

// Arrow markers for directed edges (SPEAKS_ABOUT)
svg.append("defs").selectAll("marker")
  .data(["speaks-about"])
  .join("marker")
    .attr("id",          d => `arrow-${d}`)
    .attr("viewBox",     "0 -4 8 8")
    .attr("refX",        20)
    .attr("refY",        0)
    .attr("markerWidth", 6)
    .attr("markerHeight",6)
    .attr("orient",      "auto")
  .append("path")
    .attr("d", "M0,-4L8,0L0,4")
    .attr("fill", "#9b7bbf");

const simulation = d3.forceSimulation()
  .force("link",   d3.forceLink().id(d => d.id).distance(d => 120 / Math.log(d.weight + 2)))
  .force("charge", d3.forceManyBody().strength(-280))
  .force("center", d3.forceCenter(W() / 2, H() / 2))
  .force("collide", d3.forceCollide().radius(d => nodeRadius(d) + 6));

let linkSel = g.append("g").attr("class", "links").selectAll(".link");
let nodeSel = g.append("g").attr("class", "nodes").selectAll(".node");

const tooltip = document.getElementById("tooltip");

// ── Helpers ───────────────────────────────────────────────────────────────────
function nodeRadius(d) {
  const base = d.type === "main" ? 12 : d.type === "supporting" ? 8 : 5;
  const pr   = d.pagerank || 0;
  const norm = state.maxPagerank > 0 ? pr / state.maxPagerank : 0;
  return base + norm * 16;
}

function edgeColor(d) {
  if (d.type === "DIALOGUE_WITH") {
    if (d.sentiment >  0.1) return "#f9a842";
    if (d.sentiment < -0.1) return "#5b8dee";
    return "#9b7bbf";
  }
  if (d.type === "CO_APPEARS")   return "#7ecba1";
  if (d.type === "SPEAKS_ABOUT") return "#c06090";
  return "#9b7bbf";
}

function edgeWidth(d) {
  return Math.max(1, Math.min(10, Math.sqrt(d.weight) * 1.4));
}

// ── Data loading ──────────────────────────────────────────────────────────────
async function loadData() {
  showLoading(true);
  const params = new URLSearchParams();
  if (state.season)  params.set("season",     state.season);
  if (state.episode) params.set("episode",    state.episode);
  state.relTypes.forEach(t => params.append("rel_types", t));
  params.set("min_weight", state.minWeight);

  try {
    const data = await fetch(`${API}/graph?${params}`).then(r => r.json());
    state.allData = data;
    render(data);
    updateStats(data);
  } catch (e) {
    console.error("Failed to load graph data:", e);
    showError("Cannot connect to API. Is the backend running?");
  } finally {
    showLoading(false);
  }
}

async function loadEpisodes() {
  try {
    state.episodes = await fetch(`${API}/episodes`).then(r => r.json());
    buildEpisodeDropdown();
  } catch (e) {
    console.warn("Could not load episodes:", e);
  }
}

// ── Render ────────────────────────────────────────────────────────────────────
function render({ characters, relationships }) {
  // Normalise pagerank so radius is always sensible regardless of GDS scale
  state.maxPagerank = Math.max(1, ...characters.map(c => c.pagerank || 0));

  // Filter to only characters present in relationships
  const activeIds = new Set();
  relationships.forEach(r => { activeIds.add(r.source); activeIds.add(r.target); });
  const nodes = characters.filter(c => activeIds.has(c.id));

  // Build link objects
  const nodeMap = new Map(nodes.map(n => [n.id, n]));
  const links = relationships
    .filter(r => nodeMap.has(r.source) && nodeMap.has(r.target))
    .map(r => ({ ...r }));

  // Links
  linkSel = linkSel.data(links, d => `${d.source}-${d.target}-${d.type}`)
    .join(
      enter => enter.append("line")
        .attr("class", "link")
        .attr("stroke",       d => edgeColor(d))
        .attr("stroke-width", d => edgeWidth(d))
        .attr("marker-end",   d => d.type === "SPEAKS_ABOUT" ? "url(#arrow-speaks-about)" : null)
        .call(bindLinkEvents),
      update => update
        .attr("stroke",       d => edgeColor(d))
        .attr("stroke-width", d => edgeWidth(d)),
      exit => exit.remove()
    );

  // Nodes
  nodeSel = nodeSel.data(nodes, d => d.id)
    .join(
      enter => {
        const ne = enter.append("g")
          .attr("class", d => `node ${d.type} ${!d.alive ? "revival" : ""}`)
          .call(d3.drag()
            .on("start", dragStart)
            .on("drag",  dragged)
            .on("end",   dragEnd))
          .call(bindNodeEvents);

        ne.append("circle")
          .attr("r", d => nodeRadius(d))
          .attr("fill",   d => typeColor(d))
          .attr("stroke", d => d.alive ? typeStroke(d) : "#f9d342");

        ne.append("text")
          .attr("class", "node-label")
          .attr("dy", d => nodeRadius(d) + 13)
          .attr("text-anchor", "middle")
          .text(d => shortName(d.name));

        ne.each(function(d) { drawSpeechBubble(d3.select(this), d); });

        return ne;
      },
      update => {
        update.select("circle")
          .attr("r", d => nodeRadius(d))
          .attr("fill", d => typeColor(d));
        update.select(".node-label")
          .attr("dy", d => nodeRadius(d) + 13)
          .text(d => shortName(d.name));
        update.each(function(d) {
          d3.select(this).select(".speech-bubble").remove();
          drawSpeechBubble(d3.select(this), d);
        });
        return update;
      },
      exit => exit.remove()
    );

  simulation.nodes(nodes);
  simulation.force("link").links(links);
  simulation.force("center").x(W() / 2).y(H() / 2);
  simulation.alpha(0.6).restart();

  simulation.on("tick", () => {
    linkSel
      .attr("x1", d => d.source.x)
      .attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x)
      .attr("y2", d => d.target.y);

    nodeSel.attr("transform", d => `translate(${d.x},${d.y})`);
  });
}

function typeColor(d) {
  const colors = { main: "#e8569a", supporting: "#c97bd4", guest: "#7b5ea7" };
  return colors[d.type] || "#7b5ea7";
}

function typeStroke(d) {
  const colors = { main: "#ff90c0", supporting: "#d4a0e0", guest: "#9b7bbf" };
  return colors[d.type] || "#9b7bbf";
}

function shortName(name) {
  const parts = name.split(" ");
  return parts.length > 2 ? parts[0] : name;
}

// ── Speech bubbles ────────────────────────────────────────────────────────────
function drawSpeechBubble(nodeGroup, d) {
  const words = (d.top_words || []).slice(0, 3);
  if (!words.length) return;

  const r        = nodeRadius(d);
  const label    = words.join("  ·  ");
  const fontSize = 9;
  const padX     = 9;
  const padY     = 5;
  const tailH    = 7;
  const tailW    = 10;

  // Approximate text width (monospace-ish estimate)
  const textW = label.length * fontSize * 0.58;
  const bW    = Math.max(textW + padX * 2, 40);
  const bH    = fontSize + padY * 2;

  // Bubble sits above the node: bottom of tail at -(r + 3)
  const totalH  = bH + tailH;
  const bubbleY = -(r + 3 + totalH);   // top-left y of bubble rect

  const bg = nodeGroup.append("g")
    .attr("class", "speech-bubble")
    .attr("transform", `translate(0, ${bubbleY})`);

  // Drop-shadow filter (unique per node to avoid ID clash)
  const filterId = `sf-${d.id}`;
  const defs = bg.append("defs");
  const filt = defs.append("filter").attr("id", filterId)
    .attr("x", "-20%").attr("y", "-20%")
    .attr("width", "140%").attr("height", "140%");
  filt.append("feDropShadow")
    .attr("dx", 0).attr("dy", 2)
    .attr("stdDeviation", 2)
    .attr("flood-color", "rgba(0,0,0,0.55)");

  // Combined bubble + tail as one path (seamless outline)
  const x  = -bW / 2;
  const rx = 6;
  const tw = tailW / 2;
  const bubblePath = [
    `M${x + rx},0`,
    `L${x + bW - rx},0`,
    `Q${x + bW},0 ${x + bW},${rx}`,
    `L${x + bW},${bH - rx}`,
    `Q${x + bW},${bH} ${x + bW - rx},${bH}`,
    `L${tw},${bH}`,
    `L0,${bH + tailH}`,
    `L${-tw},${bH}`,
    `L${x + rx},${bH}`,
    `Q${x},${bH} ${x},${bH - rx}`,
    `L${x},${rx}`,
    `Q${x},0 ${x + rx},0`,
    "Z",
  ].join(" ");

  bg.append("path")
    .attr("class", "bubble-bg")
    .attr("d", bubblePath)
    .attr("filter", `url(#${filterId})`);

  // Word text — single line
  bg.append("text")
    .attr("class", "bubble-word")
    .attr("x", 0)
    .attr("y", bH / 2 + fontSize * 0.36)
    .attr("text-anchor", "middle")
    .text(label);
}

// ── Drag ──────────────────────────────────────────────────────────────────────
function dragStart(event, d) {
  if (!event.active) simulation.alphaTarget(0.3).restart();
  d.fx = d.x; d.fy = d.y;
}
function dragged(event, d) { d.fx = event.x; d.fy = event.y; }
function dragEnd(event, d) {
  if (!event.active) simulation.alphaTarget(0);
  d.fx = null; d.fy = null;
}

// ── Events ────────────────────────────────────────────────────────────────────
function bindNodeEvents(sel) {
  sel
    .on("click",     onNodeClick)
    .on("mouseover", onNodeHover)
    .on("mouseout",  onNodeOut);
}

function bindLinkEvents(sel) {
  sel
    .on("mouseover", onLinkHover)
    .on("mouseout",  onLinkOut);
}

function onNodeClick(event, d) {
  event.stopPropagation();
  openCharCard(d.id);
}

function onNodeHover(event, d) {
  showTooltip(event, `<strong>${d.name}</strong><br>
    Type: ${d.type}<br>
    Scenes: ${d.scene_count}<br>
    Episodes: ${d.episode_count}<br>
    PageRank: ${(d.pagerank || 0).toFixed(3)}`);
  highlightNeighbours(d.id);
}

function onNodeOut() {
  hideTooltip();
  clearHighlight();
}

function onLinkHover(event, d) {
  const src = typeof d.source === "object" ? d.source.name : d.source;
  const tgt = typeof d.target === "object" ? d.target.name : d.target;
  const sentLabel = d.sentiment > 0.1 ? "😊 positive" : d.sentiment < -0.1 ? "😬 tense" : "😐 neutral";
  showTooltip(event, `<strong>${src} ↔ ${tgt}</strong><br>
    Type: ${d.type}<br>
    Interactions: ${d.weight}<br>
    Sentiment: ${sentLabel}`);
}

function onLinkOut() { hideTooltip(); }

function highlightNeighbours(id) {
  const neighbours = new Set([id]);
  linkSel.each(d => {
    const s = typeof d.source === "object" ? d.source.id : d.source;
    const t = typeof d.target === "object" ? d.target.id : d.target;
    if (s === id) neighbours.add(t);
    if (t === id) neighbours.add(s);
  });

  nodeSel.classed("dimmed", d => !neighbours.has(d.id));
  linkSel.classed("dimmed", d => {
    const s = typeof d.source === "object" ? d.source.id : d.source;
    const t = typeof d.target === "object" ? d.target.id : d.target;
    return !(s === id || t === id);
  });
}

function clearHighlight() {
  nodeSel.classed("dimmed", false).classed("path-highlight", false);
  linkSel.classed("dimmed", false).classed("path-highlight", false);
}

// ── Tooltip ───────────────────────────────────────────────────────────────────
function showTooltip(event, html) {
  tooltip.innerHTML = html;
  tooltip.classList.add("visible");
  moveTooltip(event);
}

function moveTooltip(event) {
  const x = event.offsetX + 14;
  const y = event.offsetY - 10;
  tooltip.style.left = `${x}px`;
  tooltip.style.top  = `${y}px`;
}

function hideTooltip() { tooltip.classList.remove("visible"); }

// ── Character card ─────────────────────────────────────────────────────────────
async function openCharCard(id) {
  const panel = document.getElementById("right-panel");
  const card  = document.getElementById("char-card-content");
  card.innerHTML = `<div class="spinner" style="margin:20px auto"></div>`;
  panel.classList.add("open");

  try {
    const c = await fetch(`${API}/character/${id}`).then(r => r.json());
    const sentBar = (v) => {
      const pct = ((v + 1) / 2 * 100).toFixed(0);
      const col = v > 0.1 ? "#f9a842" : v < -0.1 ? "#5b8dee" : "#9b7bbf";
      return `<div class="sentiment-bar" style="background:linear-gradient(90deg,${col} ${pct}%,#2d1050 ${pct}%)"></div>`;
    };

    const badgeClass = `badge-${c.type}`;
    const topRels = (c.relationships || []).slice(0, 6);

    card.innerHTML = `
      <button class="close-btn" onclick="closeCharCard()">✕</button>
      <h2>${c.name}</h2>
      <span class="char-badge ${badgeClass}">${c.type}</span>
      <div class="char-stats">
        <div class="char-stat">
          <div class="char-stat-value">${c.scene_count}</div>
          <div class="char-stat-label">Scenes</div>
        </div>
        <div class="char-stat">
          <div class="char-stat-value">${c.episode_count}</div>
          <div class="char-stat-label">Episodes</div>
        </div>
        <div class="char-stat">
          <div class="char-stat-value">${(c.pagerank || 0).toFixed(2)}</div>
          <div class="char-stat-label">PageRank</div>
        </div>
        <div class="char-stat">
          <div class="char-stat-value">${c.alive ? "✓" : "✦"}</div>
          <div class="char-stat-label">${c.alive ? "Alive" : "Revived"}</div>
        </div>
      </div>
      <h3>Top Connections</h3>
      <ul class="relation-list">
        ${topRels.map(r => `
          <li class="relation-item" onclick="openCharCard('${r.partner_id}')">
            <span class="relation-name">${r.partner_name}</span>
            <span class="relation-weight">×${r.weight}</span>
          </li>
          ${sentBar(r.sentiment || 0)}
        `).join("")}
      </ul>
      <h3>Episodes</h3>
      <div style="font-size:0.72rem;color:var(--text-muted);line-height:1.6">
        ${(c.episodes || []).map(e => `<span title="${e.title}">S${e.season}E${String(e.number).padStart(2,"0")}</span>`).join(" · ")}
      </div>
    `;

    highlightNeighbours(id);
  } catch (e) {
    card.innerHTML = `<p style="color:var(--text-muted)">Failed to load character.</p>`;
  }
}

function closeCharCard() {
  document.getElementById("right-panel").classList.remove("open");
  clearHighlight();
}

svg.on("click", () => {
  closeCharCard();
  clearHighlight();
});

// ── Shortest path ─────────────────────────────────────────────────────────────
async function findPath() {
  const from = document.getElementById("path-from").value;
  const to   = document.getElementById("path-to").value;
  const res  = document.getElementById("path-result");

  if (!from || !to || from === to) {
    res.textContent = "Select two different characters.";
    return;
  }

  res.textContent = "Finding path…";
  clearHighlight();

  try {
    const data = await fetch(`${API}/shortest-path?from=${from}&to=${to}`).then(r => r.json());
    if (data.detail) { res.textContent = "No path found."; return; }

    const pathNodeIds = new Set(data.nodes.map(n => n.id));
    const pathEdgeSet = new Set(
      data.edges.map(e => `${Math.min(e.source, e.target)}-${Math.max(e.source, e.target)}`)
    );

    nodeSel.classed("dimmed", d => !pathNodeIds.has(d.id))
           .classed("path-highlight", d => pathNodeIds.has(d.id));

    linkSel.classed("path-highlight", d => {
      const s = typeof d.source === "object" ? d.source.id : d.source;
      const t = typeof d.target === "object" ? d.target.id : d.target;
      return pathEdgeSet.has(`${Math.min(s,t)}-${Math.max(s,t)}`);
    }).classed("dimmed", d => {
      const s = typeof d.source === "object" ? d.source.id : d.source;
      const t = typeof d.target === "object" ? d.target.id : d.target;
      return !pathEdgeSet.has(`${Math.min(s,t)}-${Math.max(s,t)}`);
    });

    res.textContent = `Path length: ${data.length} step${data.length !== 1 ? "s" : ""}`;
  } catch (e) {
    res.textContent = "Error finding path.";
  }
}

function clearPath() {
  clearHighlight();
  document.getElementById("path-result").textContent = "";
}

// ── Stats ─────────────────────────────────────────────────────────────────────
function updateStats({ characters, relationships }) {
  document.getElementById("stat-chars").textContent = characters.length;
  document.getElementById("stat-rels").textContent  = relationships.length;
  const topChar = [...characters].sort((a, b) => (b.pagerank || 0) - (a.pagerank || 0))[0];
  document.getElementById("stat-top").textContent   = topChar ? shortName(topChar.name) : "—";
}

// ── Episode dropdown ──────────────────────────────────────────────────────────
function buildEpisodeDropdown() {
  const selFrom = document.getElementById("path-from");
  const selTo   = document.getElementById("path-to");

  // Will be populated with characters once data loads — called again after render
}

function populatePathSelects(characters) {
  const sorted = [...characters].sort((a, b) => b.scene_count - a.scene_count);
  const opts   = sorted.map(c => `<option value="${c.id}">${c.name}</option>`).join("");
  ["path-from", "path-to"].forEach(id => {
    const sel = document.getElementById(id);
    const cur = sel.value;
    sel.innerHTML = `<option value="">— select —</option>` + opts;
    if (cur) sel.value = cur;
  });
}

// ── Controls wiring (called from filters.js) ──────────────────────────────────
window.applyFilters = function () {
  loadData().then(() => populatePathSelects(state.allData.characters));
};

window.findPath   = findPath;
window.clearPath  = clearPath;
window.closeCharCard = closeCharCard;

// ── Loading / error ───────────────────────────────────────────────────────────
function showLoading(on) {
  document.getElementById("loading").style.display = on ? "flex" : "none";
}

function showError(msg) {
  const el = document.getElementById("loading");
  el.style.display = "flex";
  el.innerHTML = `<p style="color:#e8569a;font-size:0.9rem;text-align:center;max-width:300px">${msg}</p>
    <button class="btn" onclick="location.reload()">Retry</button>`;
}

// ── Init ──────────────────────────────────────────────────────────────────────
(async () => {
  await loadEpisodes();
  await loadData();
  populatePathSelects(state.allData.characters);
})();

window.addEventListener("resize", () => {
  simulation.force("center").x(W() / 2).y(H() / 2);
  simulation.alpha(0.1).restart();
});
