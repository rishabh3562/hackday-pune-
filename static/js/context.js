// "Context used" for one answer: real token counts, what the prompt was made of, what was NOT sent, and how the guard did.
import { h } from "./dom.js";

const COLORS = ["--chart-2", "--chart-1", "--chart-3", "--chart-5", "--chart-6", "--chart-7"];
const n = (v) => Number(v).toLocaleString();

export function contextCard(c) {
  if (!c?.calls?.length) return h("div", { class: "empty" }, "No model call for this answer (handled by code).");
  const parts = {}; c.calls.forEach((k) => k.parts.forEach((p) => (parts[p.name] = (parts[p.name] || 0) + p.tokens)));
  const names = Object.keys(parts), total = Math.max(1, Object.values(parts).reduce((a, b) => a + b, 0));
  return h("div", { class: "ctx" },
    h("div", { class: "ctx-total" }, h("b", {}, n(c.total_tokens)), h("span", { class: "mute small" }, ` tokens (${n(c.prompt_tokens)} in · ${n(c.output_tokens)} out) · ${c.calls.length} model call${c.calls.length > 1 ? "s" : ""}`)),
    h("div", { class: "ctx-bar", role: "img", "aria-label": "Prompt composition" }, names.map((k, i) => h("i", { style: `width:${(parts[k] / total) * 100}%;background:var(${COLORS[i % 6]})`, title: `${k}: ${parts[k]} tokens` }))),
    h("div", { class: "ctx-legend" }, names.map((k, i) => h("span", {}, h("i", { style: `background:var(${COLORS[i % 6]})` }), `${k} ${n(parts[k])}`))),
    h("div", { class: "ctx-calls" }, c.calls.map((k) => h("div", { class: "note-line" }, h("span", { class: "chip" }, k.label), `${k.model} · ${n(k.prompt_tokens)} in / ${n(k.output_tokens)} out${k.cached_tokens ? ` · ${n(k.cached_tokens)} cached` : ""} · ${k.ms} ms${k.exact ? "" : " (estimated)"}`))),
    h("div", { class: "note-line" }, `Latency: ${c.calls.filter((k) => k.label.startsWith("router")).reduce((a, k) => a + k.ms, 0)} ms routing · ${c.tool_ms ?? "?"} ms tools (no model) · ${c.calls.filter((k) => !k.label.startsWith("router")).reduce((a, k) => a + k.ms, 0)} ms writing`),
    c.rows_returned != null ? h("div", { class: "note-line" }, `Rows returned by the tools: ${n(c.rows_returned)} · sent to the writer: ${n(c.rows_sent)}${c.rows_returned > c.rows_sent ? " (capped)" : ""}. The full result goes to the screen directly.`) : null,
    c.guard ? h("div", { class: "note-line" }, "Grounding guard: ", h("span", { class: `badge ${c.guard === "passed first time" ? "ok" : c.guard === "regenerated once" ? "warn" : "bad"}` }, c.guard)) : null,
    h("div", { class: "note-line" }, `The model saw ${n(c.prompt_tokens)} tokens; the data it could have drawn on is ~${n(c.dataset_tokens)} tokens. That is ${c.share_of_dataset_pct}% of it, because tools compute and the model only routes and writes.`));
}
