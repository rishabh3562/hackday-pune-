// Minimal markdown for wiki pages: paragraphs, bullets, **bold**, pipe tables. Text goes through text.js, so IDs become chips.
import { h } from "./dom.js";
import { renderText } from "./text.js";

const isRow = (l) => /^\s*\|.*\|\s*$/.test(l);
const cells = (l) => l.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());

export function renderMd(md, ctx = {}) {
  const lines = String(md).split("\n"), out = []; let buf = [];
  const flush = () => { if (buf.length) out.push(renderText(buf.join("\n"), ctx)); buf = []; };
  for (let i = 0; i < lines.length; i++) {
    if (isRow(lines[i]) && lines[i + 1] && /^\s*\|[-| :]+\|\s*$/.test(lines[i + 1])) {
      flush(); const head = cells(lines[i]); const body = []; i += 2;
      while (i < lines.length && isRow(lines[i])) body.push(cells(lines[i++])); i--;
      out.push(h("div", { class: "table-wrap" }, h("table", { class: "data" }, h("thead", {}, h("tr", {}, head.map((c) => h("th", {}, c)))),
        h("tbody", {}, body.map((r) => h("tr", {}, r.map((c) => h("td", {}, renderText(c, ctx)))))))));
    } else buf.push(lines[i]);
  }
  flush();
  return h("div", { class: "md" }, out);
}
