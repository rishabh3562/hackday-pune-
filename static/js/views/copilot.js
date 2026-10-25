// Copilot: chat + a context panel that shows HOW the selected answer was produced (tool, arguments, assumptions, evidence).
import { h, clear, mount } from "../dom.js";
import { api } from "../api.js";
import { renderResult } from "../render.js";
import { renderText } from "../text.js";
import { narrateControls, stopNarration, supported } from "../narrate.js";
import { voice, onVoice, startVoice, stopVoice } from "../voice.js";
import { contextCard } from "../context.js";
import { pinAnswer } from "../report.js";
import { thread, activeChat, newChat, loadHistory, refreshChats } from "../chats.js";

const PROMPTS = [
  ["Status and the reason", "Is WELL-0001 producing oil right now? When was it last inspected, and by whom?"],
  ["Area table", "Which wells in Northeast Block 8 are not producing oil right now, and why? Show them in a table."],
  ["Ranking chart", "Which 3 wells in Northeast Block 7 had the most downtime in the last 4 months? Show a bar chart."],
  ["Heatmap", "Show a heatmap of 2026 spills by geographic area and month."],
  ["Concept search", "Which wells are failing due to mud?"],
  ["Follow the links", "What is connected to inspection INS-0001-0185?"],
];
const getMode = () => { try { return localStorage.getItem("clarifyMode") || "ask"; } catch { return "ask"; } };
function contextPanel(msg) {
  if (!msg) return [h("div", { class: "empty" }, "Select an answer to see how it was produced.")];
  const p = msg.spec.plan || {}, args = p.args || (p.calls || [])[0]?.args || {};
  const unique = [...new Set(msg.spec.citations || [])];
  const rule = msg.spec.rows?.[0]?.threshold_source;
  return [
    h("div", {}, h("h3", {}, "How I answered"), h("span", { class: "chip" }, p.tool || (p.calls || []).map((c) => c.tool).join(" + ") || p.kind || "n/a"),
      Object.entries(args).map(([k, v]) => h("span", { class: "chip" }, `${k}=${typeof v === "object" ? JSON.stringify(v) : v}`))),
    rule ? h("div", {}, h("h3", {}, "Rule source"), h("span", { class: "chip" }, rule)) : null,
    (msg.spec.notes || []).length ? h("div", {}, h("h3", {}, "Notes and assumptions"), msg.spec.notes.map((n) => h("div", { class: "note-line" }, n))) : null,
    h("div", {}, h("h3", {}, "Context used"), contextCard(msg.spec.context)),
    unique.length ? h("div", {}, h("h3", {}, `Evidence (${unique.length})`), unique.slice(0, 60).map((c) => h("span", { class: "chip" }, c))) : null,
  ];
}

export function mountCopilot(root, { user, prefill }) {
  const t = thread(user.user_id, activeChat());   // the open chat; its state lives in chats.js, keyed by (user, chat)
  loadHistory(user.user_id, t);
  t.selected ??= t.messages.filter((m) => m.role === "bot").at(-1) || null;   // kept on the thread so late answers select correctly
  const list = h("div", { class: "thread-inner" }), panel = h("aside", { class: "side-panel" });
  const input = h("textarea", { rows: 1, placeholder: "Ask a question, or teach me: “The 15 Oct reading for WELL-0164 was 41.0 °C”", "aria-label": "Message" });
  const auto = h("input", { type: "checkbox", id: "auto-read", checked: localStorage.getItem("autoRead") === "1", onchange: (e) => { try { localStorage.setItem("autoRead", e.target.checked ? "1" : "0"); } catch { /* private mode */ } } });
  const mic = h("button", { class: "btn", type: "button", title: "Voice: talk to the copilot (same tools)", onclick: () => (voice.state === "off" ? startVoice(user.user_id) : stopVoice()) }, "🎙");
  const send = h("button", { class: "btn primary", type: "button" }, "Send");

  const bubble = (m) => {
    const body = m.role === "bot" ? renderText(m.text, { onAsk: submit }) : m.text;
    const el = h("div", { class: `msg ${m.role}${m === t.selected ? " selected" : ""}` }, h("div", { class: "bubble" }, body));
    if (m.role === "bot" && m.spec?.visual !== "clarify" && m.text) { const nc = narrateControls(body, m.fresh && auto.checked); const row = nc || h("div", { class: "msg-meta" }); row.append(h("button", { class: "btn small", type: "button", title: "Pin this answer (text, charts, tables, map) to the printable report", onclick: (e) => { const prev = [...t.messages].slice(0, t.messages.indexOf(m)).reverse().find((x) => x.role === "user"); e.target.textContent = pinAnswer(prev?.text || "Question", m.spec) ? "📌 Added" : "📌 Already added"; } }, "📌 Add to report")); el.append(row); m.fresh = false; }
    if (m.role === "bot" && m.spec) {
      const v = renderResult(m.spec, { onPick: submit }); if (v) el.append(h("div", { class: "msg-visual" }, v));
      el.addEventListener("click", () => { t.selected = m; draw(); });
    }
    return el;
  };
  function hero() {
    return h("div", { class: "hero" }, h("h1", {}, "Ask your wells anything"),
      h("p", {}, "Answers come from the inspection, repair, regulator and SOP records, with the evidence shown. You can also correct data or teach a rule."),
      h("div", { class: "prompts" }, PROMPTS.map(([title, q]) => h("button", { class: "prompt", type: "button", onclick: () => submit(q) }, h("b", {}, title), h("span", {}, q)))));
  }
  function draw() {
    t.redraw = draw;                       // late answers redraw the CURRENT mount, never a detached one
    if (!root.isConnected) return;
    mount(list, t.messages.length ? t.messages.map(bubble) : t.loading ? h("div", { class: "empty" }, "Loading chat…") : hero());
    if (t.busy) list.append(h("div", { class: "msg bot" }, h("div", { class: "bubble typing" }, h("i"), h("i"), h("i"))));
    if (!t.selected) t.selected = t.messages.filter((m) => m.role === "bot").at(-1) || null;
    mount(panel, contextPanel(t.selected));
    const used = t.messages.reduce((a, m) => a + (m.spec?.context?.total_tokens || 0), 0), meter = root.querySelector("#session-tokens");
    if (meter) meter.textContent = `${used.toLocaleString()} tokens · ${t.messages.filter((m) => m.role === "bot").length} answer(s)`;
    const sc = root.querySelector(".thread"); if (sc) sc.scrollTop = sc.scrollHeight;
  }
  async function submit(text) {
    text = (text ?? input.value).trim(); if (!text || t.busy) return;
    input.value = ""; t.messages.push({ role: "user", text }); t.busy = true; t.redraw?.() ?? draw();
    try {
      const spec = await api.ask(user.user_id, t.chatId, text, getMode());
      t.selected = { role: "bot", text: spec.text, spec, fresh: true }; t.messages.push(t.selected);
    } catch (e) { t.messages.push({ role: "bot", text: `Something went wrong: ${e.message}` }); }
    t.busy = false; t.redraw?.(); refreshChats();
  }
  send.onclick = () => submit();
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } });
  input.addEventListener("input", () => { input.style.height = "auto"; input.style.height = `${input.scrollHeight}px`; });

  clear(root).append(h("div", { class: "copilot" }, h("section", { class: "chat" },
    h("div", { class: "chat-head" }, h("b", {}, "Copilot"), supported() ? h("label", { class: "small mute" }, auto, " Read answers aloud") : null, h("div", { class: "seg", role: "group", "aria-label": "Clarification mode", title: "Ask: the copilot may ask you a clarifying question with options. Auto: it never asks; it picks the most likely reading and states its assumption (used for unattended runs)." },
      [["ask", "💬 Ask me"], ["auto", "⚡ Auto"]].map(([v, label]) => h("button", { type: "button", "aria-pressed": getMode() === v, onclick: (e) => { try { localStorage.setItem("clarifyMode", v); } catch { /* private mode */ } e.currentTarget.parentElement.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b === e.currentTarget))); } }, label))),
    h("span", { class: "chip", id: "session-tokens", title: "Model tokens used in this chat (real counts from the API)" }, "0 tokens"), h("button", { class: "btn small", type: "button", onclick: () => { stopNarration(); newChat(); } }, "New chat")),
    h("div", { class: "thread" }, list), h("div", { class: "composer" }, h("div", { class: "composer-box" }, input, mic, send))), panel));
  const takeVoice = () => { for (const r of voice.pending.splice(0)) { t.messages.push({ role: "user", text: `🎙 ${r.question}` }); t.selected = { role: "bot", text: r.text, spec: r, fresh: false }; t.messages.push(t.selected); } (t.redraw ?? draw)(); };
  onVoice((e) => { if (e.type === "result" && root.isConnected) takeVoice(); });
  takeVoice(); input.focus();
  if (prefill) submit(prefill);
}
