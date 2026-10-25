// Architecture: the system diagrams (Mermaid, from docs/DIAGRAMS.md) inside the product, with live numbers.
import { h, mount } from "../dom.js";
import { api } from "../api.js";
import { renderBlocks } from "../blocks.js";
import { renderPoster } from "../poster.js";

const MERMAID = "https://cdn.jsdelivr.net/npm/mermaid@11.4.0/dist/mermaid.min.js";
let loading = null;
const loadMermaid = () => (loading ??= window.mermaid ? Promise.resolve() : new Promise((ok, no) => { const s = document.createElement("script"); s.src = MERMAID; s.onload = ok; s.onerror = no; document.head.append(s); })
  .then(() => window.mermaid.initialize({ startOnLoad: false, theme: "base", securityLevel: "loose", themeVariables: { primaryColor: "#e8f7f4", primaryBorderColor: "#0f9d8a", primaryTextColor: "#1d2433", lineColor: "#5b6577", fontFamily: "Inter, system-ui, sans-serif" } })));

export async function mountArchitecture(root, { sub }) {
  const [secs, tools, ev] = await Promise.all([api.audit("architecture"), api.audit("tools"), api.audit("evals")]);
  const poster = !sub[0] || sub[0] === "poster", idx = poster ? -1 : Math.min(Number(sub[0]), Math.max(0, secs.length - 1)), cur = secs[idx];
  const checks = ev.reduce((a, s) => a + s.total, 0), pass = ev.reduce((a, s) => a + s.passed, 0);
  const body = h("div", { class: "stack" });
  mount(root, h("div", { class: "split" }, h("aside", { class: "split-side" }, h("div", { class: "note-line" }, "Diagrams"),
    h("a", { class: `list-item${poster ? " active" : ""}`, href: "#/architecture/poster" }, h("span", {}, "★ Poster (overview)")),
    secs.map((s, i) => h("a", { class: `list-item${i === idx ? " active" : ""}`, href: `#/architecture/${i}` }, h("span", {}, `${i + 1}. ${s.title}`)))),
    h("div", { class: "view" }, h("div", { class: "page" }, h("div", { class: "page-head" }, h("div", {}, h("h1", {}, "Architecture"), h("p", { class: "mute" }, "How a question becomes a grounded answer. The LLM only routes and writes; code does the work."))),
      renderBlocks([{ type: "kpis", span: "full", items: [{ label: "Typed tools", value: tools.length }, { label: "Checks recorded", value: checks }, { label: "Passing", value: pass, tone: "ok" }, { label: "Diagrams", value: secs.length }] }]), body))));
  if (poster) { mount(body, renderPoster(), h("p", { class: "mute small" }, "Every card is a link to the page where you can inspect that component. The diagrams on the left go deeper (Mermaid).")); return; }
  if (!cur) return;
  mount(body, h("h2", {}, cur.title), h("p", { class: "arch-text" }, cur.text), ...cur.diagrams.map(() => h("div", { class: "paper" }, "Rendering…")));
  try {
    await loadMermaid();
    const holders = [...body.querySelectorAll(".paper")];
    for (let i = 0; i < holders.length; i++) { const { svg } = await window.mermaid.render(`arch-${idx}-${i}-${Date.now()}`, cur.diagrams[i]); holders[i].innerHTML = svg; }   // mermaid returns trusted SVG for our own diagram source
  } catch (e) { body.append(h("div", { class: "banner" }, `Could not render the diagram: ${e.message || e}`)); }
}
