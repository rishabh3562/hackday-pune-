// Result rendering for chat and overview: clarify options, otherwise the blocks the backend composed.
import { h } from "./dom.js";
import { renderBlocks } from "./blocks.js";

const clarify = (spec, ctx) => h("div", { class: "options" }, (spec.options || []).map((o) => h("button", { class: "option", type: "button", onclick: () => ctx.onPick?.(o) }, o)));

export function renderResult(spec, ctx = {}) {
  if (!spec) return null;
  if (spec.visual === "clarify") return clarify(spec, ctx);
  return spec.blocks?.length ? renderBlocks(spec.blocks, ctx) : null;
}
