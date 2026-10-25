// Renders a list of visualization blocks (see copilot/blocks.py). Framework-free, so the plain UI and the CopilotKit (React) UI share it.
import { h, cssVar } from "./dom.js";

// ---------- lazy third-party libs (Chart.js, Leaflet) ----------
const once = {};
const loadScript = (src) => (once[src] ??= new Promise((ok, no) => { const s = document.createElement("script"); s.src = src; s.onload = ok; s.onerror = no; document.head.append(s); }));
const loadCss = (href) => { if (!once[href]) { once[href] = 1; document.head.append(h("link", { rel: "stylesheet", href })); } };
const libs = () => { loadCss("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css");
  return Promise.all([window.Chart || loadScript("https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"), window.L || loadScript("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js")]); };

const cell = (v) => (Array.isArray(v) ? v.join(", ") : v == null ? "" : typeof v === "object" ? JSON.stringify(v) : String(v));
const fmt = (v) => (typeof v === "number" ? v.toLocaleString(undefined, { maximumFractionDigits: 1 }) : v);
const palette = () => [1, 2, 3, 4, 5, 6, 7, 8].map((i) => cssVar(`--chart-${i}`));
const TONE = { ok: "--ok", bad: "--bad", warn: "--warn", info: "--info", muted: "--mute" };
const toneColor = (t) => cssVar(TONE[t] || "--info");
const chartBox = (cls = "") => { const canvas = h("canvas"); return [h("div", { class: `chart-box ${cls}` }, canvas), canvas]; };
const axis = () => ({ ticks: { color: cssVar("--mute") }, grid: { color: cssVar("--chart-grid") } });
const draw = (canvas, cfg) => libs().then(() => new window.Chart(canvas, cfg));

function groupedScatter(b) {
  const [box, c] = chartBox("tall"), col = palette(), groups = [...new Set(b.points.map((p) => p.group))];
  draw(c, { type: "scatter", data: { datasets: groups.map((g, i) => ({ label: g, data: b.points.filter((p) => p.group === g).map((p) => ({ x: p.x, y: p.y, label: p.label })), backgroundColor: col[i % 8] + "bb", pointRadius: 3 })) },
    options: { maintainAspectRatio: false, animation: false, plugins: { legend: { labels: { color: cssVar("--mute") } }, tooltip: { callbacks: { label: (t) => t.raw.label } } }, scales: { x: { ...axis(), title: { display: true, text: b.xLabel, color: cssVar("--mute") } }, y: { ...axis(), title: { display: true, text: b.yLabel, color: cssVar("--mute") } } } } });
  return box;
}


// ---------- interactivity helpers (all optional: any failure falls back to the static render) ----------
const WELL = /^WELL-\d{4}$/;
const askFn = (ctx) => (ctx && (ctx.onAsk || ctx.onPick)) || null;   // copilot passes onPick (= submit); other pages may pass onAsk
const askAbout = (label) => (WELL.test(String(label)) ? `Is ${label} producing oil right now?` : `Tell me more about ${label}`);
const safe = (build, fallback) => { try { return build(); } catch (e) { console.warn("block interaction disabled:", e); return fallback(); } };
const num = (v) => { if (typeof v === "number") return v; if (typeof v !== "string" || v.trim() === "") return NaN; const n = Number(v.replace(/,/g, "")); return n; };
const compare = (a, b) => { const x = cell(a), y = cell(b); if (x === "" || y === "") return x === y ? 0 : x === "" ? 1 : -1;   // blanks sort last (flipped below for desc)
  const nx = num(a), ny = num(b); return !isNaN(nx) && !isNaN(ny) ? nx - ny : x.localeCompare(y, undefined, { numeric: true, sensitivity: "base" }); };
const csv = (cols, rows) => [cols, ...rows.map((r) => cols.map((k) => cell(r[k])))].map((r) => r.map((v) => (/[",\n]/.test(v) ? `"${String(v).replace(/"/g, '""')}"` : v)).join(",")).join("\n");
const download = (name, text) => { const a = h("a", { href: URL.createObjectURL(new Blob([text], { type: "text/csv" })), download: name }); document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 1000); };
const slug = (t) => (String(t || "table").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "table").slice(0, 40);
const seg = (label, on, fn, title) => h("button", { class: "btn small", type: "button", "aria-pressed": on ? "true" : "false", title, onclick: fn }, label);

function staticTable(b) {
  return h("div", { class: "table-wrap" }, h("table", { class: "data" }, h("thead", {}, h("tr", {}, b.columns.map((k) => h("th", {}, k)))),
    h("tbody", {}, b.rows.map((r) => h("tr", {}, b.columns.map((k) => h("td", {}, cell(r[k]))))))));
}

// Sortable / filterable / paged table. Default view is the same rows in the same order; extras are .blk-tools (hidden in print).
function interactiveTable(b, ctx) {
  const ask = askFn(ctx), PAGE = 25, st = { col: null, dir: 1, q: "", hidden: new Set(), limit: PAGE };
  const thead = h("tr"), tbody = h("tbody"), table = h("table", { class: "data" }, h("thead", {}, thead), tbody);
  const count = h("span", { class: "blk-count mute small", "aria-live": "polite" }), more = h("div", { class: "blk-tools blk-more" });
  const view = () => { let rows = b.rows;
    if (st.q) { const q = st.q.toLowerCase(); rows = rows.filter((r) => b.columns.some((k) => cell(r[k]).toLowerCase().includes(q))); }
    if (st.col != null) { const d = st.dir; rows = rows.map((r, i) => [r, i]).sort((x, y) => { const a = x[0][st.col], c = y[0][st.col], blank = (cell(a) === "") - (cell(c) === ""); return blank || d * compare(a, c) || x[1] - y[1]; }).map((x) => x[0]); }
    return rows; };
  const cols = () => b.columns.filter((k) => !st.hidden.has(k));
  const td = (r, k) => { const v = cell(r[k]); return h("td", {}, ask && WELL.test(v) ? h("button", { class: "cell-ask", type: "button", title: `Ask the copilot about ${v}`, onclick: () => ask(askAbout(v)) }, v) : v); };
  function paint() {
    thead.replaceChildren(...cols().map((k) => { const on = st.col === k; return h("th", { "aria-sort": on ? (st.dir > 0 ? "ascending" : "descending") : "none" },
      h("button", { class: "th-sort", type: "button", title: `Sort by ${k}`, onclick: () => { if (st.col !== k) { st.col = k; st.dir = 1; } else if (st.dir > 0) st.dir = -1; else st.col = null; st.limit = PAGE; paint(); } }, k, h("span", { class: "th-arrow", "aria-hidden": "true" }, on ? (st.dir > 0 ? " ▲" : " ▼") : ""))); }));
    const rows = view(), cs = cols();
    tbody.replaceChildren(...rows.map((r, i) => { const tr = h("tr", { class: i >= st.limit ? "pg-hidden" : null }, cs.map((k) => td(r, k))); return tr; }));
    const shown = Math.min(rows.length, st.limit);
    count.textContent = rows.length === b.rows.length ? `${rows.length} row${rows.length === 1 ? "" : "s"}` : `${rows.length} of ${b.rows.length} rows`;
    more.replaceChildren(...(rows.length > st.limit ? [h("span", { class: "mute small" }, `Showing ${shown} of ${rows.length}. `), h("button", { class: "btn small", type: "button", onclick: () => { st.limit += PAGE; paint(); } }, "Show more"), h("button", { class: "btn small", type: "button", onclick: () => { st.limit = Infinity; paint(); } }, "Show all")] : []));
  }
  const tools = [];
  if (b.rows.length > 8) tools.push(h("input", { class: "blk-filter", type: "search", placeholder: "Filter rows…", "aria-label": "Filter table rows", oninput: (e) => { st.q = e.target.value.trim(); st.limit = PAGE; paint(); } }));
  tools.push(count);
  if (b.columns.length > 2) { const menu = h("details", { class: "blk-cols" }, h("summary", { class: "btn small" }, "Columns"), h("div", { class: "blk-cols-menu" }, b.columns.map((k) => h("label", {}, h("input", { type: "checkbox", checked: true, onchange: (e) => { if (e.target.checked) st.hidden.delete(k); else if (st.hidden.size < b.columns.length - 1) st.hidden.add(k); else e.target.checked = true; paint(); } }), " ", k)))); tools.push(menu); }
  tools.push(h("button", { class: "btn small blk-csv", type: "button", title: "Download the rows now shown as CSV", onclick: () => download(`${slug(ctx?.title || b.title)}.csv`, csv(cols(), view())) }, "Download CSV"));
  paint();
  return h("div", { class: "tbl" }, h("div", { class: "blk-tools blk-bar" }, tools), h("div", { class: "table-wrap sticky" }, table), more);
}

// Bar / line with toggles (type, stacked, sort, top-N) and click-to-ask. Initial chart config equals the original one.
function chartBlock(b, ctx, kind) {
  const ask = askFn(ctx), [box, canvas] = chartBox(), st = { type: kind, stacked: !!b.stacked, sort: "none", top: 0 }, col = palette();
  let chart = null, order = b.labels.map((_, i) => i), gen = 0;
  const compute = () => { let idx = b.labels.map((_, i) => i); const tot = (i) => b.series.reduce((a, s) => a + (Number(s.values[i]) || 0), 0);
    if (st.sort === "asc") idx.sort((x, y) => tot(x) - tot(y)); else if (st.sort === "desc" || st.top) idx.sort((x, y) => tot(y) - tot(x));
    if (st.top) idx = idx.slice(0, st.top); return idx; };
  function build() {
    const my = ++gen; order = compute();
    const pick = (a) => order.map((i) => a[i]), isBar = st.type === "bar", stacked = isBar && st.stacked, f = b.flags;
    const datasets = b.series.map((s, i) => isBar ? { label: s.name, data: pick(s.values), backgroundColor: col[i % 8], borderRadius: 4 }
      : { label: s.name, data: pick(s.values), borderColor: col[i % 8], backgroundColor: col[i % 8], tension: 0.25, pointRadius: f && i === 0 ? pick(f).map((x) => (x ? 3 : 7)) : 3, pointBackgroundColor: f && i === 0 ? pick(f).map((x) => (x ? cssVar("--ok") : cssVar("--bad"))) : col[i % 8] });
    const options = { maintainAspectRatio: false, plugins: { legend: { display: b.series.length > 1, labels: { color: cssVar("--mute") } } },
      scales: { x: { ...axis(), grid: { display: false }, ...(isBar ? { stacked } : {}) }, y: isBar ? { ...axis(), stacked } : axis() } };
    if (ask) { options.onClick = (_, els) => { try { if (els.length) ask(askAbout(b.labels[order[els[0].index]])); } catch (e) { console.warn(e); } };
      options.onHover = (e, els) => { const t = e.native?.target; if (t) t.style.cursor = els.length ? "pointer" : "default"; }; }
    libs().then(() => { if (my !== gen) return; chart?.destroy(); chart = new window.Chart(canvas, { type: isBar ? "bar" : "line", data: { labels: pick(b.labels), datasets }, options }); });
  }
  const btns = {}, sync = () => { btns.bar.setAttribute("aria-pressed", st.type === "bar"); btns.line.setAttribute("aria-pressed", st.type === "line"); if (btns.stack) { btns.stack.setAttribute("aria-pressed", st.stacked); btns.stack.disabled = st.type !== "bar"; btns.stack.textContent = st.stacked ? "Stacked" : "Grouped"; } };
  const sel = (label, opts, get, set) => h("label", { class: "blk-sel" }, label + " ", h("select", { class: "select tiny", "aria-label": label, onchange: (e) => { set(e.target.value); build(); sync(); } }, opts.map(([v, t]) => h("option", { value: v, selected: String(get()) === String(v) }, t))));
  btns.bar = seg("Bar", kind === "bar", () => { st.type = "bar"; build(); sync(); }, "Show as bars"); btns.line = seg("Line", kind === "line", () => { st.type = "line"; build(); sync(); }, "Show as a line");
  const tools = [h("span", { class: "blk-seg" }, btns.bar, btns.line)];
  if (b.series.length > 1) { btns.stack = seg(st.stacked ? "Stacked" : "Grouped", st.stacked, () => { st.stacked = !st.stacked; build(); sync(); }, "Stack or group the series"); tools.push(btns.stack); }
  if (b.labels.length > 2) tools.push(sel("Sort", [["none", "Original"], ["desc", "High to low"], ["asc", "Low to high"]], () => st.sort, (v) => { st.sort = v; }));
  if (b.labels.length > 5) tools.push(sel("Show", [[0, "All"], ...[5, 10, 20].filter((n) => n < b.labels.length).map((n) => [n, `Top ${n}`])], () => st.top, (v) => { st.top = Number(v); }));
  build();
  return h("div", { class: "chart-block" }, h("div", { class: "blk-tools blk-bar" }, tools), box);
}

// Original static bar/line renderers: fallback if the interactive version throws.
const legacyBar = (b) => { const [box, c] = chartBox(); const col = palette();
  draw(c, { type: "bar", data: { labels: b.labels, datasets: b.series.map((s, i) => ({ label: s.name, data: s.values, backgroundColor: col[i % 8], borderRadius: 4 })) },
    options: { maintainAspectRatio: false, plugins: { legend: { display: b.series.length > 1, labels: { color: cssVar("--mute") } } }, scales: { x: { ...axis(), grid: { display: false }, stacked: !!b.stacked }, y: { ...axis(), stacked: !!b.stacked } } } }); return box; };
const legacyLine = (b) => { const [box, c] = chartBox(); const col = palette();
  draw(c, { type: "line", data: { labels: b.labels, datasets: b.series.map((s, i) => ({ label: s.name, data: s.values, borderColor: col[i % 8], backgroundColor: col[i % 8], tension: 0.25,
    pointRadius: b.flags && i === 0 ? b.flags.map((f) => (f ? 3 : 7)) : 3, pointBackgroundColor: b.flags && i === 0 ? b.flags.map((f) => (f ? cssVar("--ok") : cssVar("--bad"))) : col[i % 8] })) },
    options: { maintainAspectRatio: false, plugins: { legend: { display: b.series.length > 1, labels: { color: cssVar("--mute") } } }, scales: { x: { ...axis(), grid: { display: false } }, y: axis() } } }); return box; };

// ---------- renderers ----------
const R = {
  kpis: (b) => h("div", { class: "grid kpis" }, b.items.map((k) => h("div", { class: `card kpi tone-${k.tone || "none"}` }, h("span", { class: "kpi-label" }, k.label), h("span", { class: "kpi-value" }, fmt(k.value))))),
  callout: (b) => { const span = b.text ? h("span", {}, b.text) : null, el = h("div", { class: `callout ${b.tone}` }, h("b", {}, b.title), span);
    if (span && b.text.length > 280) { try { span.classList.add("clamp"); const t = h("button", { class: "btn small blk-tools callout-more", type: "button", "aria-expanded": "false", onclick: () => { const open = span.classList.toggle("clamp") === false; t.textContent = open ? "Show less" : "Show more"; t.setAttribute("aria-expanded", open); } }, "Show more"); el.append(t); } catch { /* keep full text */ } }
    return el; },
  status: (b) => { const c = b.card, st = (k, v) => h("div", { class: "stat" }, h("small", {}, k), cell(v));
    return h("div", { class: "stat-grid" }, h("div", { class: "stat" }, h("small", {}, `${c.well} · ${c.type} · ${c.area}`), h("span", { class: `badge status-pill ${c.producing ? "ok" : "bad"}` }, c.producing ? "PRODUCING" : "NOT PRODUCING")),
      st("Wellhead °C", c.wellhead_temp_c), st("Air °C", c.ambient_temp_c), st("Above air", `${c.delta_c} (limit ${c.threshold_c})`), st("Inspected", `${c.inspected_at} · ${c.inspected_by}`),
      st("Recorded status", c.recorded_status + (c.recorded_status_stale ? " (out of date)" : "")), st("Inspection", c.inspection), st("Rule source", c.threshold_source)); },
  table: (b, ctx) => safe(() => interactiveTable(b, ctx), () => staticTable(b)),
  bar: (b, ctx) => safe(() => chartBlock(b, ctx, "bar"), () => legacyBar(b)),
  line: (b, ctx) => safe(() => chartBlock(b, ctx, "line"), () => legacyLine(b)),
  donut: (b, ctx) => { const [box, c] = chartBox(), ask = askFn(ctx), options = { maintainAspectRatio: false, cutout: "62%", plugins: { legend: { position: "right", labels: { color: cssVar("--mute"), boxWidth: 12 } } } };
    if (ask) { options.onClick = (_, els) => { try { if (els.length) ask(askAbout(b.labels[els[0].index])); } catch (e) { console.warn(e); } };
      options.onHover = (e, els) => { const t = e.native?.target; if (t) t.style.cursor = els.length ? "pointer" : "default"; }; }
    draw(c, { type: "doughnut", data: { labels: b.labels, datasets: [{ data: b.values, backgroundColor: palette(), borderColor: cssVar("--surface") }] }, options }); return box; },
  scatter: (b) => { if (b.points[0]?.group !== undefined) return groupedScatter(b); const [box, c] = chartBox(), pts = (flag) => b.points.filter((p) => p.flag === flag).map((p) => ({ x: p.x, y: p.y, label: p.label }));
    draw(c, { type: "scatter", data: { datasets: [{ label: "Producing", data: pts(true), backgroundColor: cssVar("--ok") }, { label: "Not producing", data: pts(false), backgroundColor: cssVar("--bad"), pointRadius: 7 }] },
      options: { maintainAspectRatio: false, plugins: { legend: { labels: { color: cssVar("--mute") } }, tooltip: { callbacks: { label: (t) => `${t.raw.label}: ${t.raw.x}°C air, ${t.raw.y}°C wellhead` } } },
        scales: { x: { ...axis(), title: { display: true, text: b.xLabel, color: cssVar("--mute") } }, y: { ...axis(), title: { display: true, text: b.yLabel, color: cssVar("--mute") } } } } }); return box; },
  code: (b) => h("pre", { class: "code" }, b.text),
  heatmap: (b) => { const max = Math.max(1, ...b.values.flat());
    return h("div", { class: "table-wrap" }, h("table", { class: "data heat" }, h("thead", {}, h("tr", {}, h("th", {}, ""), b.cols.map((c) => h("th", {}, c)))),
      h("tbody", {}, b.rowLabels.map((rl, i) => h("tr", {}, h("td", {}, rl), b.values[i].map((v) => h("td", { style: `background:color-mix(in srgb, var(--brand) ${Math.round((v / max) * 85)}%, transparent)` }, v))))))); },
  map: (b, ctx) => { const box = h("div", { class: "map-box" }), ask = askFn(ctx), tones = [...new Set(b.pins.map((p) => p.tone || "info"))];
    const NAME = { ok: "OK", bad: "Problem", warn: "Warning", info: "Info", muted: "Other" };
    libs().then(() => { const m = window.L.map(box, { scrollWheelZoom: false });
      window.L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18, attribution: "© OpenStreetMap" }).addTo(m);
      const marks = b.pins.map((p) => { const mk = window.L.circleMarker([p.lat, p.lon], { radius: 9, color: toneColor(p.tone), fillOpacity: 0.6 }).addTo(m);
        let pop = `<b>${p.label}</b><br>${p.detail || ""}`;
        try { mk.bindTooltip(String(p.label)); if (ask) { const q = askAbout(p.label); pop = h("div", {}, h("b", {}, p.label), h("br"), p.detail || "", h("br"), h("button", { class: "btn small", type: "button", onclick: () => ask(q) }, `Ask about ${p.label}`)); } } catch { /* plain popup */ }
        return mk.bindPopup(pop); });
      marks.length > 1 ? m.fitBounds(window.L.featureGroup(marks).getBounds().pad(0.3)) : m.setView([b.pins[0].lat, b.pins[0].lon], 13); });
    return tones.length > 1 || b.pins.length > 1 ? h("div", { class: "map-block" }, box, h("div", { class: "map-legend", "aria-label": "Map legend" }, tones.map((t) => h("span", {}, h("i", { style: `background:${toneColor(t)}` }), NAME[t] || t)), h("span", { class: "mute" }, ask ? "Click a pin to ask about it" : ""))) : box; },
  timeline: (b) => h("ol", { class: "timeline" }, b.events.map((e) => h("li", { style: `--dot:${toneColor(e.tone)}` }, h("span", { class: "tl-date" }, e.date), h("b", {}, e.title), h("span", { class: "mute small" }, e.detail)))),
};

export function renderBlocks(blocks, ctx = {}) {
  const items = (blocks || []).filter((b) => R[b.type]).map((b) => {
    const body = R[b.type](b, ctx), wrapped = ["table", "heatmap", "status", "timeline", "bar", "line", "donut", "scatter", "map", "code"].includes(b.type);
    return h("section", { class: `block span-${b.span || "half"} t-${b.type}` }, b.title && wrapped ? h("h2", { class: "card-title" }, b.title) : null, body);
  });
  const root = h("div", { class: "blocks" }, items);
  // Controls inside a block must not bubble to the chat message's "select this answer" handler, which redraws the thread and would reset the control state.
  root.addEventListener("click", (e) => { try { if (e.target.closest?.("button, select, input, summary, label, canvas, .leaflet-container, th")) e.stopPropagation(); } catch { /* ignore */ } });
  return root;
}
