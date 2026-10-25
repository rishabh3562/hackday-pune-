// Overview: the zero-prompt morning briefing. Every attention item opens the copilot with its question.
import { h, clear } from "../dom.js";
import { api } from "../api.js";
import { renderBlocks } from "../blocks.js";
import { pinBriefing } from "../report.js";

const kpi = (k) => h("div", { class: `card kpi tone-${k.tone || "none"}` }, h("span", { class: "kpi-label" }, k.label), h("span", { class: "kpi-value" }, Number(k.value).toLocaleString()));

const attention = (items, ask) => h("div", { class: "attention" }, items.length ? items.map((a) =>
  h("button", { class: `attn ${a.level}`, type: "button", onclick: () => ask(a.ask) }, h("i", { class: "dot" }), h("div", {}, h("b", {}, a.title), h("span", {}, a.detail)), h("span", { class: "go" }, "Ask copilot →")))
  : h("div", { class: "empty" }, "Nothing needs attention."));

const areas = (rows) => h("div", {}, rows.map((a) => h("div", { class: "area-row" },
  h("div", {}, h("b", {}, a.area), h("div", { class: "small mute" }, `${a.wells} wells${a.stale ? ` · ${a.stale} stale status` : ""}`)),
  h("div", { class: "meter", title: `${a.producing} producing, ${a.stopped} stopped` }, h("i", { style: `width:${(a.producing / a.wells) * 100}%` })),
  h("span", { class: `badge ${a.stopped ? "bad" : "ok"}` }, a.stopped ? `${a.stopped} stopped` : "all producing"))));

export async function mountOverview(root, { user, ask }) {
  clear(root).append(h("div", { class: "page" }, h("div", { class: "page-head" }, h("div", {}, h("h1", {}, `Good day, ${user.name.split(" ")[0]}`), h("p", { id: "ov-sub", class: "mute" }, "Loading the briefing…")), h("button", { class: "btn primary", id: "print-brief", type: "button", hidden: true }, "Print briefing"))));
  const page = root.firstChild;
  let b;
  try { b = await api.briefing(); } catch (e) { page.append(h("div", { class: "banner" }, `Could not load the briefing: ${e.message}`)); return; }
  const pb = page.querySelector("#print-brief"); pb.hidden = false; pb.onclick = () => { pinBriefing(b); location.hash = "#/report"; };
  page.querySelector("#ov-sub").textContent = `Fleet briefing as of ${b.today}. Click an item to dig in with the copilot.`;
  page.append(
    h("div", { class: "grid kpis" }, b.kpis.map(kpi)),
    h("div", { class: "grid two" },
      h("section", { class: "card" }, h("h2", {}, "Needs attention"), attention(b.attention, ask)),
      h("section", { class: "card" }, h("h2", {}, "Areas"), areas(b.areas))),
    h("div", { class: "grid two" },
      h("section", { class: "card" }, h("h2", {}, "Most downtime, last 4 months (days)"), renderBlocks([b.downtime], { onAsk: ask })),
      h("section", { class: "card" }, h("h2", {}, "Wells not producing now"), renderBlocks([b.stopped], { onAsk: ask }))),
    h("section", { class: "card" }, h("h2", {}, `Spills by area and month, ${b.today.slice(0, 4)}`), renderBlocks([b.heatmap])));
}
