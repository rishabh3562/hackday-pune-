// Turns answer text into readable, highlighted DOM: paragraphs, bullets, **bold**, entity chips (wells, records, rules, numbers, dates) and
// colour-coded status words. Every word is a span so narration can highlight it. Never uses innerHTML.
import { h } from "./dom.js";

const PATTERNS = [
  ["well", /WELL-\d{4}/], ["rec", /(?:INS|MNT|CTX|REG)-\d{4}-\d{3,4}/], ["rule", /\b(?:SR|RC|WS)-0\d\b/],
  ["date", /\b20\d\d-\d\d-\d\d\b/], ["num", /(?:USD|\$)\s?[\d,]+(?:\.\d+)?|\b\d[\d,]*(?:\.\d+)?\s?(?:°C|bbl|barrels?|days?|hours?|h|%|psi)\b/],
  ["bad", /\b(?:stopped producing|not producing|NOT PRODUCING|breach(?:es|ed)?|overdue|late|violation|fine[ds]?|shut in|down)\b/i],
  ["ok", /\b(?:is producing|IS producing|confirmed|on time|met)\b/i],
  ["warn", /\b(?:out of date|unconfirmed|no recorded reason|disagree[sd]?|conflict|assumed|stale|pending|open)\b/i],
];
const TOKEN = new RegExp(PATTERNS.map(([k, r]) => `(?<${k}>${r.source})`).join("|"), "gi");

// "**bold**" first, then entity tokens inside every piece of plain text
function inline(text, ctx) {
  const out = [];
  text.split(/(\*\*[^*]+\*\*)/).forEach((part) => {
    if (!part) return;
    const bold = /^\*\*(.+)\*\*$/.exec(part);
    const nodes = tokens(bold ? bold[1] : part, ctx);
    out.push(bold ? h("strong", {}, nodes) : nodes);
  });
  return out;
}
function tokens(text, ctx) {
  const out = []; let last = 0;
  for (const m of text.matchAll(TOKEN)) {
    if (m.index > last) out.push(words(text.slice(last, m.index)));
    const kind = Object.keys(m.groups).find((k) => m.groups[k] != null);
    const clickable = (kind === "well" || kind === "rec") && ctx.onAsk;
    const ask = kind === "well" ? `Is ${m[0]} producing oil right now?` : `What is connected to ${m[0]}?`;
    out.push(h(clickable ? "button" : "span", { class: `ent ${kind}`, type: clickable ? "button" : null, title: clickable ? `Ask about ${m[0]}` : null, onclick: clickable ? () => ctx.onAsk(ask) : null }, words(m[0])));
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(words(text.slice(last)));
  return out;
}
const words = (s) => s.split(/(\s+)/).map((w) => (/^\s+$/.test(w) || !w ? w : h("span", { class: "w" }, w)));

export function renderText(text, ctx = {}) {
  const root = h("div", { class: "prose" });
  let list = null;
  for (const line of String(text).split("\n")) {
    const li = /^\s*(?:[-*•]|\d+[.)])\s+(.*)$/.exec(line);
    if (li) { if (!list) { list = h("ul"); root.append(list); } list.append(h("li", {}, inline(li[1], ctx))); continue; }
    list = null;
    if (line.trim() && !/^\s*\|?[-| :]+\|?\s*$/.test(line)) root.append(h("p", {}, inline(line.replace(/^\s*\|\s*|\s*\|\s*$/g, "").replace(/\s*\|\s*/g, " · "), ctx)));
  }
  return root;
}
