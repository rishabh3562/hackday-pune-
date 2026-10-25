// For judges: each challenge requirement and award category -> the feature, where to see it, and live evidence.
import { h, mount } from "../dom.js";
import { api } from "../api.js";
import { renderBlocks } from "../blocks.js";

const REQS = [
  ["Copilot chat with generative UI", "Typed result blocks (KPIs, callouts, tables, bar/line/donut/scatter, heatmap, map, timeline), several per answer; chart switching by chat", "#/copilot", "Ask: “Is WELL-0001 producing oil right now?”", "blocks"],
  ["Answers grounded in the data, with evidence", "34 deterministic tools + hybrid doc search; every answer cites record IDs; a grounding guard and a critic sub-agent check the prose", "#/audit/traces", "Open a trace: plan, tool, evidence, tokens", "golden"],
  ["Memory: shared knowledge", "Notes, corrections and rules by any user are visible to everyone, with author and scope", "#/knowledge", "Teach: “FYI WELL-0007 will be shut in from 17 Oct for 10 days”", "design-review"],
  ["Memory: private per user", "“The wells we discussed…” resolves only from that user's own history, by time and count", "#/audit/memory", "Switch user and ask the same recall question", "design-review"],
  ["Learning from feedback at the right scope", "Corrections with selectors (one well, many rows, a well type), revoke/supersede, original kept, conflicts shown", "#/knowledge", "Correct a reading, then ask again as another user", "design-review"],
  ["Honesty about conflicts", "Claims are checked against the latest inspection and stored confirmed/unconfirmed; both sides kept", "#/copilot", "Say “WELL-0175 is running fine”", "design-review"],
  ["Holds up on new data", "One re-runnable ingest over any number of roots, rules parsed from documents with fallbacks, fake test-set rehearsal", "#/audit/ingest", "See lineage, orphans, rule-parse warnings", "extra"],
  ["Best use of Gemma 4", "The planner runs on Gemma 4 26B-A4B (Vertex) with a measured router benchmark vs Gemini", "#/audit/evaluations", "See router-gemini / router-gemma", "router-gemma"],
  ["Best open-source AI project", "Chroma, DuckDB, BM25, CopilotKit + AG-UI, LiveKit, Mermaid, Playwright", "#/audit/vectors", "Browse the Chroma collection and query it", "embeddings"],
];

export async function mountScorecard(root, { nav }) {
  const ev = await api.audit("evals"), tools = await api.audit("tools"), by = Object.fromEntries(ev.map((s) => [s.suite, s]));
  const tot = ev.reduce((a, s) => a + s.total, 0), ok = ev.reduce((a, s) => a + s.passed, 0);
  const rows = REQS.map(([req, feat, link, tryit, suite]) => ({ Requirement: req, "How it is built": feat, "Try it": tryit, Evidence: by[suite] ? `${by[suite].suite}: ${by[suite].passed}/${by[suite].total}` : "see Audit", Where: link }));
  mount(root, h("div", { class: "page" }, h("div", { class: "page-head" }, h("div", {}, h("h1", {}, "For judges"), h("p", { class: "mute" }, "Every requirement and award category, where to see it, and the live evidence behind it. All numbers come from the last real runs in tests/results."))),
    renderBlocks([{ type: "kpis", span: "full", items: [{ label: "Typed tools", value: tools.length }, { label: "Checks recorded", value: tot }, { label: "Passing", value: ok, tone: "ok" }, { label: "Suites", value: ev.length }] },
      { type: "callout", span: "full", tone: "info", title: "Honest reading of the numbers", text: "Scenario suites were written by the builder and tuned against failures; the unseen final questions are the real test. Several checks involve a model, so results can vary between runs. Everything is reproducible from tests/." }]),
    h("div", { class: "card" }, h("h2", {}, "Requirements and where to see them"), h("div", { class: "table-wrap" }, h("table", { class: "data" }, h("thead", {}, h("tr", {}, Object.keys(rows[0]).map((k) => h("th", {}, k)))),
      h("tbody", {}, rows.map((r) => h("tr", {}, Object.entries(r).map(([k, v]) => h("td", {}, k === "Where" ? h("a", { class: "btn small", href: v }, "Open") : v)))))))),
    h("div", { class: "card stack" }, h("h2", {}, "Pages for inspection"), h("div", {}, ["Overview: briefing + live KPIs", "Copilot: chat, voice, context panel per answer", "Wiki: per well / type / fleet pages", "Knowledge: everything users taught, revocable", "QA: layers of verification, how and why, real results and history", "Audit: Context, Answers vs expected, Traces, Evaluations, Vector store, Data & ingest, Rules, Tools, Prompts, Memory, Health", "Architecture: 11 diagrams"].map((t) => h("div", { class: "note-line" }, "• " + t))))));
}
