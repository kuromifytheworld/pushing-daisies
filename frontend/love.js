/* Love Story Tab — Ned & Chuck relationship evidence */

const LOVE_DATA_URL = (window.API_BASE || "http://localhost:8000") + "/api/love-story";

// ── Highlight love keywords inside a line of text ────────────────────────────
const LOVE_WORDS = new Set([
  "love","touch","alive","dead","together","miss","heart","never","always",
  "promise","beautiful","feel","close","hand","breath","real","dream","wish",
  "want","need","forever","apart","hold","kiss","soul","only","mine","yours",
  "fate","chance","afraid","safe","warm","wait","stay","leave","perfect","enough"
]);

function highlightLine(text) {
  return text.replace(/\b([a-zA-Z']+)\b/g, (w) =>
    LOVE_WORDS.has(w.toLowerCase()) ? `<em>${w}</em>` : w
  );
}

// ── Build quote cards ─────────────────────────────────────────────────────────
function renderQuotes(quotes) {
  const grid = document.getElementById("quote-grid");
  grid.innerHTML = "";

  quotes.forEach(q => {
    const isNedFirst = q.speaker1 === "Ned";
    const s1class    = isNedFirst ? "ned"   : "chuck";
    const s2class    = isNedFirst ? "chuck" : "ned";

    const card = document.createElement("div");
    card.className = "quote-card";
    card.innerHTML = `
      <div class="ep-badge">${q.episode} · ${q.title}</div>
      <div class="exchange">
        <div class="utterance">
          <div class="speaker-dot ${s1class}"></div>
          <div class="line-text">"${highlightLine(q.line1)}"</div>
        </div>
        <div class="utterance">
          <div class="speaker-dot ${s2class}"></div>
          <div class="line-text">"${highlightLine(q.line2)}"</div>
        </div>
      </div>
    `;
    grid.appendChild(card);
  });
}

// ── D3 sentiment arc timeline ─────────────────────────────────────────────────
function renderTimeline(timeline) {
  const el  = document.getElementById("love-chart");
  const W   = el.clientWidth || 600;
  const H   = 140;
  const pad = { top: 18, right: 16, bottom: 30, left: 36 };

  d3.select(el).selectAll("*").remove();
  const svg = d3.select(el).append("svg")
    .attr("width", W).attr("height", H);

  const x = d3.scalePoint()
    .domain(timeline.map(d => d.id))
    .range([pad.left, W - pad.right])
    .padding(0.3);

  const y = d3.scaleLinear()
    .domain([-0.5, 0.5])
    .range([H - pad.bottom, pad.top]);

  // Zero line
  svg.append("line")
    .attr("x1", pad.left).attr("x2", W - pad.right)
    .attr("y1", y(0)).attr("y2", y(0))
    .attr("stroke", "rgba(255,255,255,0.08)")
    .attr("stroke-dasharray", "3,4");

  // Gradient area fill
  const grad = svg.append("defs").append("linearGradient")
    .attr("id", "love-grad").attr("x1",0).attr("y1",0).attr("x2",0).attr("y2",1);
  grad.append("stop").attr("offset","0%")
    .attr("stop-color","#e8569a").attr("stop-opacity",0.45);
  grad.append("stop").attr("offset","100%")
    .attr("stop-color","#e8569a").attr("stop-opacity",0.02);

  const area = d3.area()
    .x(d => x(d.id))
    .y0(y(0))
    .y1(d => y(d.sentiment))
    .curve(d3.curveCatmullRom);

  const line = d3.line()
    .x(d => x(d.id))
    .y(d => y(d.sentiment))
    .curve(d3.curveCatmullRom);

  svg.append("path").datum(timeline)
    .attr("fill", "url(#love-grad)")
    .attr("d", area);

  svg.append("path").datum(timeline)
    .attr("fill", "none")
    .attr("stroke", "#e8569a")
    .attr("stroke-width", 2)
    .attr("d", line);

  // Season separator (after S01E09)
  const sepX = (x("S01E09") + x("S02E01")) / 2;
  svg.append("line")
    .attr("x1", sepX).attr("x2", sepX)
    .attr("y1", pad.top).attr("y2", H - pad.bottom)
    .attr("stroke", "rgba(255,255,255,0.12)")
    .attr("stroke-dasharray", "4,3");
  svg.append("text")
    .attr("x", sepX - 4).attr("y", pad.top + 2)
    .attr("text-anchor","end").attr("fill","rgba(255,255,255,0.3)")
    .attr("font-size","8px").text("S1");
  svg.append("text")
    .attr("x", sepX + 4).attr("y", pad.top + 2)
    .attr("text-anchor","start").attr("fill","rgba(255,255,255,0.3)")
    .attr("font-size","8px").text("S2");

  // Y axis
  svg.append("g").call(
    d3.axisLeft(y).tickValues([-0.4,-0.2,0,0.2,0.4])
      .tickFormat(d => d > 0 ? `+${d}` : d)
      .tickSize(3)
  )
  .attr("transform", `translate(${pad.left},0)`)
  .call(g => g.select(".domain").remove())
  .call(g => g.selectAll("text").attr("fill","rgba(255,255,255,0.35)").attr("font-size","9px"))
  .call(g => g.selectAll("line").attr("stroke","rgba(255,255,255,0.12)"));

  // Dots + tooltip
  const tooltip = document.getElementById("love-chart-tooltip");

  svg.selectAll(".ep-dot")
    .data(timeline)
    .join("circle")
      .attr("class", "ep-dot")
      .attr("cx", d => x(d.id))
      .attr("cy", d => y(d.sentiment))
      .attr("r",  d => d.exchange_count > 30 ? 5 : 3.5)
      .attr("fill", d => d.sentiment > 0.05 ? "#f9d342" : d.sentiment < -0.05 ? "#5b8dee" : "#e8569a")
      .attr("stroke", "#0e0520")
      .attr("stroke-width", 1.5)
      .style("cursor","pointer")
      .on("mouseover", (event, d) => {
        const label = d.sentiment >= 0 ? "💛 tender" : "💔 tense";
        tooltip.innerHTML =
          `<strong>${d.id}</strong> — ${d.title}<br>` +
          `Sentiment: ${d.sentiment > 0 ? "+" : ""}${d.sentiment} ${label}<br>` +
          `Exchanges: ${d.exchange_count}`;
        tooltip.classList.add("vis");
      })
      .on("mousemove", event => {
        tooltip.style.left = (event.clientX + 12) + "px";
        tooltip.style.top  = (event.clientY - 10) + "px";
      })
      .on("mouseout", () => tooltip.classList.remove("vis"));
}

// ── Mini Ned↔Chuck relationship graph ─────────────────────────────────────────
async function renderMiniGraph(quotes) {
  const el = document.getElementById("love-minigraph");
  const W  = el.clientWidth  || 300;
  const H  = el.clientHeight || 280;

  d3.select(el).selectAll("*").remove();

  // Fetch Ned & Chuck specific data from API
  let nedData, chuckData;
  try {
    const base = window.API_BASE || "http://localhost:8000";
    [nedData, chuckData] = await Promise.all([
      fetch(`${base}/api/character/ned`).then(r=>r.json()),
      fetch(`${base}/api/character/chuck`).then(r=>r.json()),
    ]);
  } catch(e) {
    el.innerHTML = `<p style="color:var(--text-muted);font-size:0.75rem;padding:12px">Could not load graph data.</p>`;
    return;
  }

  // Build nodes: Ned, Chuck, their shared connections
  const sharedPartners = new Map();
  (nedData.relationships||[]).forEach(r => sharedPartners.set(r.partner_id, r));
  const chuckRels = new Map((chuckData.relationships||[]).map(r=>[r.partner_id,r]));

  // Only partners connected to BOTH
  const mutual = [...sharedPartners.keys()].filter(id => chuckRels.has(id) && id !== 'ned' && id !== 'chuck').slice(0,6);

  const nodes = [
    { id: "ned",   name: "Ned",   type: "main",  r: 26, color: "#e8569a" },
    { id: "chuck", name: "Chuck", type: "main",  r: 22, color: "#f9d342" },
    ...mutual.map(id => ({
      id, name: sharedPartners.get(id).partner_name,
      type: "supporting", r: 9, color: "#c97bd4"
    }))
  ];

  const nedRel   = sharedPartners.get("chuck") || { weight: 0, sentiment: 0 };
  const links = [
    { source:"ned", target:"chuck", weight: nedRel.weight, sentiment: nedRel.sentiment, main: true },
    ...mutual.map(id => ({ source:"ned",   target:id, weight: sharedPartners.get(id).weight, main:false })),
    ...mutual.map(id => ({ source:"chuck", target:id, weight: chuckRels.get(id).weight, main:false })),
  ];

  const svg = d3.select(el).append("svg").attr("width",W).attr("height",H);

  // Central love beam between Ned & Chuck
  const defs = svg.append("defs");
  const lg = defs.append("linearGradient").attr("id","love-beam")
    .attr("x1","0%").attr("y1","0%").attr("x2","100%").attr("y2","0%");
  lg.append("stop").attr("offset","0%").attr("stop-color","#e8569a").attr("stop-opacity",0.9);
  lg.append("stop").attr("offset","100%").attr("stop-color","#f9d342").attr("stop-opacity",0.9);

  const sim = d3.forceSimulation(nodes)
    .force("link",   d3.forceLink(links).id(d=>d.id).distance(d => d.main ? 80 : 70).strength(0.6))
    .force("charge", d3.forceManyBody().strength(-200))
    .force("center", d3.forceCenter(W/2, H/2))
    .force("collide", d3.forceCollide().radius(d=>d.r+8));

  const linkSel = svg.append("g").selectAll("line")
    .data(links).join("line")
      .attr("stroke",       d => d.main ? "url(#love-beam)" : "rgba(200,150,220,0.25)")
      .attr("stroke-width", d => d.main ? 3 : Math.max(1, d.weight/60))
      .attr("stroke-dasharray", d => d.main ? null : "3,3");

  // Pulse animation on the central link
  linkSel.filter(d=>d.main)
    .append("animate")
    .attr("attributeName","stroke-opacity")
    .attr("values","0.7;1;0.7").attr("dur","2s").attr("repeatCount","indefinite");

  const nodeSel = svg.append("g").selectAll("g")
    .data(nodes).join("g")
      .call(d3.drag()
        .on("start", (e,d)=>{ if(!e.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; })
        .on("drag",  (e,d)=>{ d.fx=e.x; d.fy=e.y; })
        .on("end",   (e,d)=>{ if(!e.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }));

  nodeSel.append("circle")
    .attr("r",      d => d.r)
    .attr("fill",   d => d.color)
    .attr("stroke", "#0e0520")
    .attr("stroke-width", 2);

  // Glow for Ned & Chuck
  nodeSel.filter(d=>d.id==="ned"||d.id==="chuck")
    .append("circle")
      .attr("r",    d => d.r + 8)
      .attr("fill", "none")
      .attr("stroke", d => d.color)
      .attr("stroke-width", 1)
      .attr("stroke-opacity", 0.3);

  nodeSel.append("text")
    .attr("text-anchor","middle")
    .attr("dy", d => d.r + 13)
    .attr("fill","rgba(255,255,255,0.8)")
    .attr("font-size", d => d.type==="main" ? "11px" : "9px")
    .attr("font-family","Georgia,serif")
    .text(d => d.name.split(" ")[0]);

  // "can never touch ♥" label on the central link
  const touchLabel = svg.append("text")
    .attr("text-anchor","middle")
    .attr("fill","rgba(232,86,154,0.7)")
    .attr("font-size","8px")
    .attr("font-style","italic")
    .text("can never touch ♥");

  sim.on("tick", () => {
    linkSel
      .attr("x1", d=>d.source.x).attr("y1", d=>d.source.y)
      .attr("x2", d=>d.target.x).attr("y2", d=>d.target.y);
    nodeSel.attr("transform", d=>`translate(${d.x},${d.y})`);

    const nedNode   = nodes.find(n=>n.id==="ned");
    const chuckNode = nodes.find(n=>n.id==="chuck");
    if (nedNode && chuckNode) {
      touchLabel
        .attr("x", (nedNode.x + chuckNode.x)/2)
        .attr("y", (nedNode.y + chuckNode.y)/2 - 8);
    }
  });
}

// ── Stats ─────────────────────────────────────────────────────────────────────
function renderStats(data) {
  const totalExchanges = data.timeline.reduce((s,t)=>s+t.exchange_count,0);
  const avgSentiment   = (data.timeline.reduce((s,t)=>s+t.sentiment,0)/data.timeline.length).toFixed(2);
  const peakEp         = [...data.timeline].sort((a,b)=>b.sentiment-a.sentiment)[0];

  document.getElementById("love-stat-exchanges").textContent  = totalExchanges;
  document.getElementById("love-stat-sentiment").textContent  = avgSentiment > 0 ? `+${avgSentiment}` : avgSentiment;
  document.getElementById("love-stat-peak").textContent       = peakEp.id;
  document.getElementById("love-stat-episodes").textContent   = data.timeline.filter(t=>t.exchange_count>0).length;
}

// ── Open / close ──────────────────────────────────────────────────────────────
let loveLoaded = false;

window.openLoveTab = async function () {
  document.getElementById("love-panel").classList.add("open");
  if (loveLoaded) return;
  loveLoaded = true;

  try {
    const data = await fetch(LOVE_DATA_URL).then(r => r.json());
    renderTimeline(data.timeline);
    renderQuotes(data.quotes);
    renderStats(data);
    renderMiniGraph(data.quotes);
  } catch (e) {
    console.error("Love story load failed:", e);
  }
};

window.closeLoveTab = function () {
  document.getElementById("love-panel").classList.remove("open");
};
