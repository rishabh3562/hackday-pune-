// Wiki: a living page per well, per well type, and one central fleet page. Facts are live from the data; insights are model-written, cited, cached.
import { h, clear, mount } from "../dom.js";
import { api } from "../api.js";
import { renderMd } from "../md.js";

let indexCache = null;
const chips = (ids) => (ids || []).map((c) => h("span", { class: "chip" }, c));

function insightsCard(p, regenerate) {
  const ins = p.insights;
  const head = h("div", { class: "fact-head" }, h("h2", { class: "card-title", style: "margin:0" }, "Insights"), h("span", { class: "badge info" }, "model-written, checked against the facts"),
    ins && p.insights_stale ? h("span", { class: "badge warn" }, "stale: the facts changed since this was written") : null,
    h("button", { class: "btn small", style: "margin-left:auto", type: "button", onclick: regenerate }, ins ? "Regenerate" : "Generate insights"));
  if (!ins) return h("section", { class: "card stack" }, head, h("div", { class: "empty" }, "No insights generated yet. They are written once from the facts below and cached."));
  return h("section", { class: "card stack" }, head,
    h("ul", { class: "insights" }, ins.insights.map((i) => h("li", {}, h("span", {}, i.text), h("div", {}, chips(i.sources))))),
    ins.suggested_checks?.length ? h("div", {}, h("div", { class: "note-line" }, "Suggested checks"), h("ul", { class: "insights" }, ins.suggested_checks.map((c) => h("li", {}, c)))) : null,
    h("div", { class: "small mute" }, `${ins.model} · ${ins.generated_at} · ${ins.dropped ? `${ins.dropped} unsupported claim(s) dropped by the checker` : "all claims checked against the facts"}`));
}

function pageView(p, nav, reload) {
  const ask = (q) => (/^Is (WELL-\d{4})/.exec(q) ? nav.wiki("well", /WELL-\d{4}/.exec(q)[0]) : nav.copilot(q));
  const prompt = { well: `Is ${p.id} producing oil right now, and what is its history?`, type: `Which wells of type ${p.id} need a root-cause analysis on their pump jack?`, fleet: "What needs attention across the field right now?" }[p.kind];
  return h("div", { class: "page" },
    h("div", { class: "page-head" }, h("div", {}, h("h1", {}, p.title), h("p", { class: "mute" }, `Facts are generated live from the data and corrections log (as of ${p.as_of}, fingerprint ${p.facts_hash}).`)),
      h("div", { class: "filters" }, h("button", { class: "btn primary", type: "button", onclick: () => nav.copilot(prompt) }, "Ask the copilot about this"),
        h("button", { class: "btn", type: "button", onclick: () => nav.copilot(p.kind === "well" ? `The ... reading for ${p.id} is wrong, the real value is ...` : "Note for this scope: ...", false) }, "Correct or teach"))),
    insightsCard(p, async (e) => { e.target.disabled = true; e.target.textContent = "Writing…"; await fetch(`/api/wiki/${p.kind}/${p.id}/insights`, { method: "POST" }); reload(); }),
    ...p.sections.map((s) => h("section", { class: "card", id: s.id }, h("h2", {}, s.title), renderMd(s.md, { onAsk: ask }))),
    h("details", { class: "card" }, h("summary", {}, "Raw facts (JSON) behind this page"), h("pre", { class: "code" }, JSON.stringify(p.facts, null, 2))));
}

export async function mountWiki(root, { sub, nav }) {
  const [kind = "fleet", id = "all"] = sub;
  indexCache ??= await api.wikiIndex();
  const q = h("input", { class: "select", placeholder: "Search wells…", "aria-label": "Search wells" }), list = h("div", { class: "wiki-list" });
  const entry = (label, meta, key, dot) => h("button", { class: `list-item${key === `${kind}/${id}` ? " active" : ""}`, type: "button", onclick: () => nav.wiki(...key.split("/")) }, dot ? h("i", { class: `dot ${dot}` }) : null, h("span", {}, label), h("span", { class: "mute small" }, meta));
  const drawList = () => {
    const s = q.value.toLowerCase();
    mount(list, entry("Fleet (central)", "all wells", "fleet/all"), h("div", { class: "note-line" }, "Well types"), indexCache.types.map((t) => entry(t.id, `${t.wells} wells`, `type/${t.id}`)),
      h("div", { class: "note-line" }, "Wells"), indexCache.wells.filter((w) => !s || `${w.id} ${w.area} ${w.type}`.toLowerCase().includes(s)).map((w) => entry(w.id, `${w.type}${w.taught ? " · taught" : ""}`, `well/${w.id}`, w.producing ? "ok" : "bad")));
  };
  q.addEventListener("input", drawList);
  const body = h("div", { class: "view" });
  mount(root, h("div", { class: "split" }, h("aside", { class: "split-side" }, q, list), body)); drawList();
  const load = async () => { mount(body, h("div", { class: "page" }, h("div", { class: "empty" }, "Loading…"))); try { const p = await api.wiki(kind, id); mount(body, pageView(p, nav, load)); } catch (e) { mount(body, h("div", { class: "page" }, h("div", { class: "banner" }, `Could not load: ${e.message}`))); } };
  load();
}
