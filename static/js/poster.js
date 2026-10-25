// The architecture poster: one data structure, rendered as colour-coded lanes of component cards (used in the app, in poster.html and for the PNG export).
import { h } from "./dom.js";

const LANES = [
  { id: "in", emoji: "🙋", title: "Ask", tone: "--chart-5", note: "Any front door, same brain", nodes: [
    ["🖥️", "Web UI", "Overview · Copilot · Wiki · Report", "#/overview"], ["🎙️", "Voice", "LiveKit + Gemini Live, same tools", "#/copilot"], ["🧩", "CopilotKit", "AG-UI streaming add-on", ""], ["🔌", "FastAPI", "/api/ask · /agui · /api/voice", "#/audit/health"]] },
  { id: "understand", emoji: "🧠", title: "Understand", tone: "--chart-2", note: "1 LLM call → a JSON plan", arrow: "plan", nodes: [
    ["🧭", "Planner", "Gemini 2.5 Flash · Gemma 4 selectable · repairs malformed plans", "#/audit/prompts"], ["❓", "Clarify loop", "2-4 grounded options + free text · confirm big changes", "#/copilot"], ["🔁", "Re-render", "“show it as a table” without re-querying", "#/copilot"],
    ["✏️", "Statement handlers", "corrections · rules · notes · claims · undo", "#/knowledge"]] },
  { id: "act", emoji: "⚙️", title: "Act (no LLM)", tone: "--chart-3", note: "34 typed tools do all the arithmetic", arrow: "tool calls", nodes: [
    ["🛢️", "Status & trend", "producing? why? last inspection", "#/audit/tools"], ["📉", "Downtime · spills · costs", "windows, rankings, heatmaps", "#/audit/tools"], ["⚖️", "Compliance", "SR-01..03 · RC-01..05 · RCA", "#/audit/tools"], ["🧬", "Root causes", "which wells fail from X · why one well failed", "#/audit/tools"],
    ["🕸️", "Trace", "walk ID links, no graph DB", "#/audit/tools"], ["🔎", "Doc search", "hybrid BM25 + Chroma vectors, passage-level", "#/audit/vectors"], ["🧮", "SQL (last resort)", "read-only, validated, shown", "#/audit/tools"]] },
  { id: "know", emoji: "🗄️", title: "Remember & retrieve", tone: "--chart-7", note: "Each data shape gets its store", arrow: "typed rows", nodes: [
    ["📊", "Records", "pandas frames (compute) · DuckDB for SQL + exported system of record", "#/audit/ingest"], ["🧾", "Corrections log", "SQLite overlay · selectors · revoke/supersede", "#/knowledge"], ["💬", "Conversation memory", "per user · time · entity IDs", "#/audit/memory"],
    ["📚", "Chroma + BM25", "1.7k passages · 768-d · metadata filters", "#/audit/vectors"], ["📏", "Rules registry", "thresholds with document section", "#/audit/rules"], ["📖", "Wiki", "per well · type · fleet", "#/wiki"]] },
  { id: "answer", emoji: "✍️", title: "Answer & verify", tone: "--chart-1", note: "Facts in, checked prose out", arrow: "facts only", nodes: [
    ["✍️", "Writer", "sees the tool result, never raw data", "#/audit/prompts"], ["🛡️", "Grounding guard", "IDs · numbers · every row · no “row excluded”; regenerate once", "#/audit/prompts"], ["🕵️", "Critic sub-agent", "Gemini 2.5 Pro reviews every written answer (not docs / SQL / trace)", "#/audit/prompts"],
    ["🧩", "Blocks composer", "4-8 visual blocks per answer, 0 tokens", "#/copilot"], ["🧮", "Context meter", "real tokens per model call", "#/audit/context"]] },
  { id: "show", emoji: "🖼️", title: "Show", tone: "--chart-8", note: "Generative UI, auditable", arrow: "blocks + evidence", nodes: [
    ["📈", "Charts & maps", "bar · line · donut · scatter · heatmap · map", "#/copilot"], ["🕒", "Timeline & KPIs", "events, callouts, status tiles", "#/overview"], ["🖨️", "Report", "pin answers → print / PDF", "#/report"], ["🔊", "Read-aloud", "word highlighting", "#/copilot"], ["🏗️", "Architecture", "this page", "#/architecture"]] },
];
const PROVE = { emoji: "✅", title: "Prove it", tone: "--chart-4", note: "Everything is inspectable", nodes: [
  ["🧪", "Test suites", "golden · extra · design review · blocks · SQL · embeddings · critic", "#/audit/evals"], ["🧑‍⚖️", "LLM judge", "stronger model grades real answers", "#/audit/answers"], ["🔬", "Traces", "plan, tool, latency, tokens per answer", "#/audit/traces"],
  ["📐", "Context engineering", "tokens vs source data", "#/audit/context"], ["🧱", "Ingest lineage", "orphans, rule-parse warnings", "#/audit/ingest"], ["⭐", "For judges", "requirement → evidence", "#/judges"]] };

const card = (tone, [emoji, name, sub, link]) => h(link ? "a" : "div", { class: "pcard", href: link || null, style: `--tone:var(${tone})`, title: `${name}: ${sub}` }, h("span", { class: "pemoji" }, emoji), h("b", {}, name), h("span", {}, sub));
const lane = (l) => h("section", { class: "plane", style: `--tone:var(${l.tone})` },
  l.arrow ? h("div", { class: "parrow" }, h("i", {}, "▼"), h("span", {}, l.arrow)) : null,
  h("div", { class: "plane-body" }, h("div", { class: "plane-label" }, h("span", {}, l.emoji), h("b", {}, l.title), h("small", {}, l.note)), h("div", { class: "pcards" }, l.nodes.map((n) => card(l.tone, n)))));

export function renderPoster() {
  return h("div", { class: "poster" }, h("div", { class: "poster-head" }, h("h2", {}, "🛢️ Asset Intelligence Copilot"), h("p", {}, "The LLM only routes and writes. Typed tools compute. Code verifies. Every step is inspectable.")),
    h("div", { class: "poster-grid" }, h("div", { class: "poster-main" }, LANES.map(lane)), h("aside", { class: "plane prove", style: `--tone:var(${PROVE.tone})` },
      h("div", { class: "plane-label" }, h("span", {}, PROVE.emoji), h("b", {}, PROVE.title), h("small", {}, PROVE.note)), h("div", { class: "pcards col" }, PROVE.nodes.map((n) => card(PROVE.tone, n))))));
}
