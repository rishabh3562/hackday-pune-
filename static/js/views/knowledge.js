// Knowledge: everything users taught the copilot. Originals are never overwritten; revoked items stay as audit history.
import { h, clear, mount } from "../dom.js";
import { api } from "../api.js";

const TONE = { confirmed: "ok", unconfirmed: "warn", revoked: "", superseded: "", conflict: "bad" };
const KINDS = ["all", "correction", "rule", "note", "claim"];

export async function mountKnowledge(root) {
  let data, kind = "all";
  const body = h("div", { class: "page" });
  const draw = () => {
    const rows = data.facts.filter((f) => kind === "all" || f.kind === kind);
    mount(body,
      h("div", { class: "page-head" }, h("div", {}, h("h1", {}, "Knowledge & corrections"), h("p", {}, "What the team has taught the copilot. Corrections apply to every user; nothing overwrites the original data."))),
      data.conflicts.length ? h("div", { class: "banner" }, `${data.conflicts.length} overlapping corrections with different values: the more specific, later one wins.`) : null,
      h("div", { class: "filters" }, KINDS.map((k) => h("button", { class: "btn small", type: "button", "aria-pressed": k === kind, onclick: () => { kind = k; draw(); } }, k))),
      rows.length ? rows.map((f) => h("div", { class: "card fact" },
        h("div", { class: "fact-head" }, h("span", { class: `badge ${TONE[f.status] ?? ""}` }, f.status), h("b", {}, `#${f.id} ${f.kind}`),
          h("span", { class: "mute small" }, `${f.author_name} · ${f.ts.slice(0, 16).replace("T", " ")}`),
          !["revoked", "superseded"].includes(f.status) ? h("button", { class: "btn small ghost", type: "button", style: "margin-left:auto", onclick: async () => { await api.revoke(f.id); data = await api.facts(); draw(); } }, "Revoke") : null),
        h("div", {}, f.kind === "correction" ? `${f.field}: ${f.original || ""} → ${f.op && f.op !== "set" ? f.op + " " : ""}${f.corrected}` : f.text),
        h("div", { class: "small mute" }, [`scope: ${f.scope_type} ${(f.scope_id || "").slice(0, 70)}`, f.inspection_id, f.reason && `why: ${f.reason.slice(0, 120)}`].filter(Boolean).join(" · "))))
        : h("div", { class: "card empty" }, "Nothing here yet. Tell the copilot a correction, a rule or a note and it will appear."));
  };
  clear(root).append(body); body.append(h("div", { class: "empty" }, "Loading…"));
  data = await api.facts(); draw();
}
