// Audit: everything a judge (or an engineer) needs to inspect how answers are produced. One tab per concern.
import { h, mount } from "../dom.js";
import { api } from "../api.js";
import { renderBlocks } from "../blocks.js";
import { renderText } from "../text.js";

const table = (columns, rows, title) => ({ type: "table", title, columns, rows, span: "full" });
const kpis = (items) => ({ type: "kpis", items, span: "full" });
const callout = (tone, title, text) => ({ type: "callout", tone, title, text, span: "full" });
const view = (...b) => renderBlocks(b.flat());
const chips = (ids) => (ids || []).map((c) => h("span", { class: "chip" }, c));
const badge = (ok) => h("span", { class: `badge ${ok ? "ok" : "bad"}` }, ok ? "pass" : "FAIL");

const score = (j) => (j?.scores ? Math.round((Object.values(j.scores).reduce((a, b) => a + b, 0) / Object.values(j.scores).length) * 10) / 10 : null);
const TABS = {
  vectors: ["Vector store", async () => {
    const v = await api.vectors(); if (v.error) return h("div", { class: "banner" }, v.error);
    const qbox = h("input", { class: "select", placeholder: "Try a query, e.g. how quickly must a leak be contained", style: "flex:1" }), qout = h("div", { class: "stack" });
    const kind = h("select", { class: "select", style: "width:auto" }, h("option", { value: "" }, "all kinds"), Object.keys(v.kinds).map((k) => h("option", { value: k }, k))), bq = h("input", { class: "select", placeholder: "filter text / id…", style: "flex:1" }), bout = h("div", {});
    const run = async () => { if (!qbox.value.trim()) return; mount(qout, h("div", { class: "empty" }, "Embedding the query…")); const r = await api.vquery(qbox.value);
      mount(qout, view(table(["rank", "id", "kind", "cosine", "text"], r.vector_only, `Vector-only ranking (cosine, ${r.store})`), table(["rank", "doc", "kind", "section", "snippet"], r.hybrid, "Hybrid result (BM25 + vectors, boosted: what the agent actually gets)"))); };
    qbox.addEventListener("keydown", (e) => e.key === "Enter" && run());
    const browse = async () => { const r = await api.vbrowse(kind.value, bq.value); mount(bout, view(table(["id", "kind", "well", "well_type", "text"], r, `${r.length} stored chunks (Chroma get, with metadata)`))); };
    kind.onchange = browse; bq.addEventListener("keydown", (e) => e.key === "Enter" && browse()); browse();
    return h("div", { class: "stack" }, view(kpis([{ label: "Store", value: v.store }, { label: "Chunks", value: v.chunks }, { label: "Dimensions", value: v.dim }, { label: "Chroma on disk (MB)", value: Math.round(v.chroma_bytes / 1e5) / 10 }]),
      callout("info", "What this is", `${v.model} embeddings, persisted in Chroma at ${v.chroma_path} (rebuilt from the embedding cache ${v.embedding_cache_bytes ? Math.round(v.embedding_cache_bytes / 1e5) / 10 + " MB" : ""}, so nothing is re-embedded). HNSW: ${v.hnsw || "n/a"}. Kinds: ${JSON.stringify(v.kinds)}.`),
      { type: "scatter", title: "2-D map of all chunk embeddings (PCA), coloured by document kind", points: v.points, xLabel: "component 1", yLabel: "component 2", span: "full" }),
      h("div", { class: "card stack" }, h("h2", {}, "Live query"), h("div", { class: "filters" }, qbox, h("button", { class: "btn primary", type: "button", onclick: run }, "Search")), qout),
      h("div", { class: "card stack" }, h("h2", {}, "Browse the collection"), h("div", { class: "filters" }, kind, bq, h("button", { class: "btn", type: "button", onclick: browse }, "Filter")), bout)); }],
  context: ["Context", async () => {
    const c = await api.audit("context");
    if (!c.n) return h("div", { class: "empty" }, "No answers with token data yet. Ask the copilot a few questions and come back.");
    const rows = c.answers, cum = rows.reduce((a, r) => (a.push((a.at(-1) || 0) + r.total), a), []);
    return h("div", { class: "stack" }, view(kpis([{ label: "Answers measured", value: c.n }, { label: "Avg tokens / answer", value: c.avg_total }, { label: "Total tokens", value: c.total_tokens }, { label: "Source data (tokens)", value: c.dataset_tokens }]),
      { type: "bar", title: "Tokens per query (prompt vs output)", labels: rows.map((r, i) => `${i + 1}`), series: [{ name: "prompt", values: rows.map((r) => r.prompt) }, { name: "output", values: rows.map((r) => r.output) }], span: "half" },
      { type: "line", title: "Cumulative tokens", labels: rows.map((r, i) => `${i + 1}`), series: [{ name: "tokens", values: cum }], span: "half" },
      { type: "donut", title: "What the average prompt is made of", labels: c.composition.map((x) => x.part), values: c.composition.map((x) => x.avg_tokens), span: "half" },
      table(["technique", "what", "number"], c.techniques, "Context engineering: what we do, with measured numbers"),
      table(["ts", "question", "total", "prompt", "output", "calls", "rows_returned", "rows_sent", "guard", "ms"], rows.slice().reverse(), "Per query")));
  }],
  answers: ["Answers vs expected", async () => {
    const a = await api.audit("answers"); let suite = "all", only = "all";
    const judged = a.filter((x) => x.judge?.scores), avg = judged.length ? Math.round((judged.reduce((t, x) => t + score(x.judge), 0) / judged.length) * 100) / 100 : "n/a";
    const list = h("div", { class: "stack" }), suites = ["all", ...new Set(a.map((x) => x.suite))];
    const draw = () => mount(list, a.filter((x) => (suite === "all" || x.suite === suite) && (only === "all" || (only === "issues" && (x.ok === false || (x.judge && x.judge.verdict !== "pass"))))).map((x) => h("details", { class: "card", open: x.ok === false },
      h("summary", {}, h("b", {}, x.id), badge(x.ok !== false), x.judge?.verdict ? h("span", { class: `badge ${x.judge.verdict === "pass" ? "ok" : x.judge.verdict === "partial" ? "warn" : "bad"}` }, `judge: ${x.judge.verdict} ${score(x.judge) ?? ""}`) : null,
        h("span", { class: "mute small" }, x.suite), h("span", {}, x.question.slice(0, 110))),
      h("div", { class: "grid two" }, h("div", { class: "card" }, h("h2", {}, "Expected"), h("div", { class: "prose" }, x.expected)), h("div", { class: "card" }, h("h2", {}, "Actual answer"), renderText(x.actual))),
      x.judge?.scores ? h("div", {}, Object.entries(x.judge.scores).map(([k, v]) => h("span", { class: `badge ${v >= 4 ? "ok" : v >= 3 ? "warn" : "bad"}`, style: "margin-right:4px" }, `${k} ${v}`)), (x.judge.issues || []).map((i) => h("div", { class: "note-line" }, i))) : null,
      x.dialogue ? h("div", {}, h("div", { class: "note-line" }, "Dialogue in this scenario"), x.dialogue.map((d) => h("div", { class: "note-line" }, `${d.user}: ${d.q}  →  ${d.a.slice(0, 220)}`))) : null,
      h("div", {}, x.tool ? h("span", { class: "chip" }, x.tool) : null, (x.blocks || []).map((b) => h("span", { class: "chip" }, b)), (x.citations || []).slice(0, 12).map((c) => h("span", { class: "chip" }, c))))));
    const chip = (label, get, set) => h("div", { class: "filters" }, label, ...[].concat(get).map((v) => h("button", { class: "btn small", type: "button", "aria-pressed": v === (label === "Suite: " ? suite : only), onclick: () => { set(v); draw(); mount(bar, bars()); } }, v)));
    const bars = () => [chip("Suite: ", suites, (v) => (suite = v)), chip("Show: ", ["all", "issues"], (v) => (only = v))];
    const bar = h("div", { class: "stack" }, bars()); draw();
    return h("div", { class: "stack" }, view(kpis([{ label: "Answers recorded", value: a.length }, { label: "Judged", value: judged.length }, { label: "Judge avg score (1-5)", value: avg, tone: "ok" }, { label: "Judge pass", value: judged.filter((x) => x.judge.verdict === "pass").length, tone: "ok" }]),
      callout("info", "How to read this", "Expected facts come from the challenge's example-questions document (given) or from independent pandas ground truth (extra). The LLM judge is a stronger model than the writer and scores correctness, grounding, completeness, honesty and clarity.")), bar, list);
  }],
  traces: ["Traces", async () => {
    const t = await api.audit("traces"); const avg = (k) => (t.length ? Math.round(t.reduce((a, x) => a + (x[k] || 0), 0) / t.length) : 0);
    const q = h("input", { class: "select", placeholder: "Filter traces…" }), list = h("div", { class: "stack" });
    const draw = () => mount(list, t.filter((x) => `${x.question} ${x.plan?.tool || x.plan?.kind}`.toLowerCase().includes(q.value.toLowerCase())).map((x) => h("details", { class: "card trace" },
      h("summary", {}, h("span", { class: "mute small" }, x.ts.slice(11, 19)), h("b", {}, x.question.slice(0, 90)), h("span", { class: "chip" }, x.plan?.tool || x.plan?.kind), h("span", { class: "chip" }, `${x.ms ?? "?"} ms`), h("span", { class: "chip" }, `${x.llm_calls ?? "?"} LLM`), h("span", { class: "chip" }, `~${x.approx_tokens ?? "?"} tok`), x.mode ? h("span", { class: "chip" }, x.mode) : null),
      h("div", { class: "stack" }, h("div", { class: "note-line" }, "Plan the planner returned"), h("pre", { class: "code" }, JSON.stringify(x.plan, null, 2)),
        x.blocks?.length ? h("div", {}, h("span", { class: "note-line" }, "Blocks: "), chips(x.blocks)) : null, (x.notes || []).map((n) => h("div", { class: "note-line" }, n)),
        h("div", { class: "note-line" }, "Answer"), h("div", {}, x.answer), h("div", {}, h("span", { class: "note-line" }, "Evidence: "), chips(x.citations))))));
    q.addEventListener("input", draw); draw();
    return h("div", { class: "stack" }, view(kpis([{ label: "Answers logged", value: t.length }, { label: "Avg latency (ms)", value: avg("ms") }, { label: "Avg LLM calls", value: Math.round(avg("llm_calls") * 10) / 10 }, { label: "Avg tokens", value: avg("approx_tokens") }])), q, list);
  }],
  evals: ["Evaluations", async () => {
    const r = await api.audit("evals"); const tot = r.reduce((a, s) => a + s.total, 0), ok = r.reduce((a, s) => a + s.passed, 0);
    return h("div", { class: "stack" }, view(kpis([{ label: "Checks recorded", value: tot }, { label: "Passing", value: ok, tone: "ok" }, { label: "Suites", value: r.length }])),
      r.length ? r.map((s) => h("details", { class: "card", open: s.passed < s.total }, h("summary", {}, h("b", {}, s.suite), h("span", { class: `badge ${s.passed === s.total ? "ok" : "bad"}` }, `${s.passed}/${s.total}`), h("span", { class: "mute small" }, s.ran_at),
        s.tool_kind_accuracy != null ? h("span", { class: "chip" }, `tool ${s.tool_kind_accuracy}/${s.total} · tool+args ${s.tool_args_accuracy}/${s.total}`) : null),
        h("div", { class: "table-wrap" }, h("table", { class: "data" }, h("tbody", {}, s.items.map((i) => h("tr", {}, h("td", {}, i.id), h("td", {}, badge(i.ok)), h("td", {}, i.desc, i.core ? h("span", { class: "badge info", style: "margin-left:6px" }, "core") : null, i.info ? h("div", { class: "small mute" }, i.info) : null))))))))
        : h("div", { class: "empty" }, "No results yet. Run the suites in tests/ (they write tests/results/*.json).")); }],
  ingest: ["Data & ingest", async () => {
    const d = await api.audit("ingest"); const row = (k, v) => ({ Check: k, Value: v });
    return view(kpis(d.tables.slice(0, 5).map((t) => ({ label: t.table, value: t.rows }))), table(["table", "rows", "from", "range", "parsed"], d.tables, "What was loaded"),
      table(["Check", "Value"], Object.entries(d.orphans).map(([k, v]) => row(k, v)), "Referential integrity (orphans)"),
      table(["Check", "Value"], [row("dataset roots", d.roots.join(", ")), row("'today' (one config value)", d.today), row("well types", JSON.stringify(d.well_types)), row("DuckDB system of record", d.duckdb.path + (d.duckdb.bytes ? ` (${(d.duckdb.bytes / 1e6).toFixed(1)} MB)` : "")),
        row("embeddings cache", d.embeddings_cache_bytes ? `${(d.embeddings_cache_bytes / 1e6).toFixed(1)} MB` : "n/a")], "Pipeline"),
      ...d.warnings.map((w) => callout(d.warnings[0].startsWith("none") ? "ok" : "warn", "Rule parsing", w))); }],
  rules: ["Rules", async () => { const r = await api.audit("rules");
    return view(table(["rule", "value", "source", "origin"], r.registry, "Rules registry (value and the document section it came from)"), table(["id", "rule", "value", "by", "status", "text"], r.overrides, "User overrides (scoped, audited)")); }],
  tools: ["Tools", async () => { const t = await api.audit("tools"); return view(kpis([{ label: "Deterministic tools", value: t.length }]), table(["name", "args", "description"], t, "What the planner can call (no LLM inside any of them)")); }],
  prompts: ["Prompts & models", async () => { const p = await api.audit("prompts");
    return h("div", { class: "stack" }, view(table(["Role", "Model"], Object.entries(p.models).map(([k, v]) => ({ Role: k, Model: Array.isArray(v) ? v.join(", ") : v })), "Models"), callout("info", "Grounding guard", p.guard)),
      h("div", { class: "card" }, h("h2", {}, "Router prompt (rendered, sent with every question)"), h("pre", { class: "code" }, p.router)), h("div", { class: "card" }, h("h2", {}, "Writer prompt"), h("pre", { class: "code" }, p.writer))); }],
  memory: ["Memory", async () => { const m = await api.audit("memory");
    return h("div", { class: "stack" }, view(callout("info", "Privacy model", m.note)), m.users.length ? m.users.map((u) => h("details", { class: "card" }, h("summary", {}, h("b", {}, u.user), h("span", { class: "chip" }, `${u.turns} turns`), h("span", { class: "mute small" }, u.last)),
      h("div", { class: "stack" }, u.recent.map((t) => h("div", { class: "note-line" }, `${t.ts.slice(11, 16)} ${t.role}: ${t.text.slice(0, 160)}`, t.entities && t.entities !== "[]" ? h("span", { class: "chip" }, t.entities) : null))))) : h("div", { class: "empty" }, "No conversations yet."));
  }],
  health: ["Health", async () => { const x = await api.audit("health");
    return view(kpis([{ label: "Uptime (s)", value: x.uptime_s }, { label: "LLM calls this run", value: x.llm.calls }, { label: "Facts logged", value: x.facts_logged }, { label: "Wells", value: x.wells }]),
      table(["Setting", "Value"], [["clarify mode", x.mode], ["confirm large changes over (rows)", x.confirm_rows], ["today", x.today], ["data roots", x.data_roots.join(", ")], ["approx tokens in / out (chars/4)", `${Math.round(x.llm.in_chars / 4)} / ${Math.round(x.llm.out_chars / 4)}`]].map(([Setting, Value]) => ({ Setting, Value })))); }],
};

export async function mountAudit(root, { sub }) {
  const tab = TABS[sub[0]] ? sub[0] : "traces", body = h("div", { class: "stack" });
  mount(root, h("div", { class: "page" }, h("div", { class: "page-head" }, h("div", {}, h("h1", {}, "Audit"), h("p", { class: "mute" }, "Inspect how every answer was produced: traces, evaluations, data lineage, rules, tools, prompts, memory."))),
    h("div", { class: "filters" }, Object.entries(TABS).map(([k, [label]]) => h("a", { class: "btn small", href: `#/audit/${k}`, "aria-pressed": k === tab }, label))), body));
  mount(body, h("div", { class: "empty" }, "Loading…"));
  try { mount(body, await TABS[tab][1]()); } catch (e) { mount(body, h("div", { class: "banner" }, `Could not load: ${e.message}`)); }
}
