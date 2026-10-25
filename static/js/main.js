// App shell: sidebar navigation, user switcher, theme, hash routing. Views are mounted into #view.
import { h, clear, mount, initials } from "./dom.js";
import { api } from "./api.js";
import { mountOverview } from "./views/overview.js";
import { mountCopilot } from "./views/copilot.js";
import { mountKnowledge } from "./views/knowledge.js";
import { mountWiki } from "./views/wiki.js";
import { mountAudit } from "./views/audit.js";
import { mountArchitecture } from "./views/architecture.js";
import { mountScorecard } from "./views/scorecard.js";
import { mountReport } from "./report.js";
import { mountQA } from "./views/qa.js";
import { chatPanel, useUser, onActive, freshIfUsed } from "./chats.js";
import { voice, onVoice, startVoice, stopVoice, sendVoiceText } from "./voice.js";

const NAV = [["overview", "▦", "Overview"], ["copilot", "✦", "Copilot"], ["wiki", "✎", "Wiki"], ["knowledge", "❖", "Knowledge"], ["audit", "⚖", "Audit"], ["architecture", "◇", "Architecture"], ["qa", "✔", "QA"], ["report", "⎙", "Report"], ["judges", "★", "For judges"]];
const store = { get: (k, d) => { try { return localStorage.getItem(k) ?? d; } catch { return d; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch { /* private mode */ } } };
const state = { users: [], userId: store.get("user", "U-201"), theme: store.get("theme", "auto"), chatsOpen: store.get("chatsOpen", "1") === "1" };
const app = document.getElementById("app");
const applyTheme = () => state.theme === "auto" ? document.documentElement.removeAttribute("data-theme") : document.documentElement.setAttribute("data-theme", state.theme);
const me = () => state.users.find((u) => u.user_id === state.userId) || state.users[0];
const parts = () => (location.hash.replace("#/", "") || "overview").split("/");
const route = () => parts()[0];

function copilotItem(icon, label, cur) {   // accordion: the Copilot item expands to New chat + recent chats
  const open = state.chatsOpen;
  const toggle = () => { state.chatsOpen = !state.chatsOpen; store.set("chatsOpen", state.chatsOpen ? "1" : "0"); render(); };
  return h("div", { class: `nav-group${open ? " open" : ""}` },
    h("div", { class: "nav-row" },
      h("button", { class: "nav-item", type: "button", "aria-current": cur === "copilot" ? "page" : null, onclick: () => { if (!state.chatsOpen) { state.chatsOpen = true; store.set("chatsOpen", "1"); } go("copilot"); } }, h("span", {}, icon), h("span", { class: "nav-label" }, label)),
      h("button", { class: "nav-caret", type: "button", "aria-expanded": String(open), "aria-controls": "chat-sub", title: open ? "Hide chats" : "Show chats", "aria-label": open ? "Hide chats" : "Show chats", onclick: toggle }, open ? "▾" : "▸")),
    open ? chatPanel() : null);
}

function sidebar() {
  const cur = route();
  return h("aside", { class: "sidebar" },
    h("div", { class: "brand" }, h("span", { class: "brand-mark" }, "🛢"), h("div", {}, "Asset Copilot", h("small", {}, "Oil-field intelligence"))),
    h("nav", { class: "nav" }, NAV.map(([id, icon, label]) => id === "copilot" ? copilotItem(icon, label, cur) :
      h("button", { class: "nav-item", type: "button", "aria-current": id === cur ? "page" : null, onclick: () => go(id) }, h("span", {}, icon), h("span", { class: "nav-label" }, label)))),
    h("div", { class: "spacer" }),
    h("div", { class: "user-card" },
      h("div", { class: "user-row" }, h("span", { class: "avatar" }, initials(me().name)), h("div", {}, h("b", {}, me().name), h("div", { class: "small mute" }, me().role.replace(/_/g, " ")))),
      h("select", { class: "select", "aria-label": "Switch user", onchange: (e) => { state.userId = e.target.value; store.set("user", state.userId); render(); } },
        state.users.map((u) => h("option", { value: u.user_id, selected: u.user_id === state.userId }, u.name))),
      h("div", { class: "seg", role: "group", "aria-label": "Theme" }, [["auto", "◐", "Auto"], ["light", "☀", "Light"], ["dark", "☾", "Dark"]].map(([v, icon, label]) =>
        h("button", { type: "button", title: `${label} theme`, "aria-pressed": state.theme === v, onclick: () => { state.theme = v; store.set("theme", v); applyTheme(); render(); } }, icon, h("span", { class: "nav-label" }, " " + label))))));
}

export function go(view, params = {}) {   // the hashchange event is the single trigger for rendering a new view
  state.params = params;
  if (location.hash === `#/${view}`) render(); else location.hash = `#/${view}`;
}

function dock() {
  const panel = h("div", { class: "voice-panel", hidden: true }), fab = h("button", { class: "voice-fab", type: "button", title: "Talk to the copilot (Gemini Live voice, same tools as the chat)", "aria-label": "Voice" }, "🎙");
  const input = h("input", { class: "select", placeholder: "…or type to the voice agent", "aria-label": "Type to the voice agent" });
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && input.value.trim()) { sendVoiceText(input.value.trim()); input.value = ""; } });
  const draw = () => {
    const on = voice.state !== "off"; fab.classList.toggle("on", on); fab.dataset.state = voice.state; panel.hidden = !on;
    mount(panel, h("div", { class: "voice-head" }, h("b", {}, "Voice"), h("span", { class: `badge ${voice.state === "speaking" ? "info" : voice.state === "listening" ? "ok" : ""}` }, voice.state),
      h("button", { class: "btn small", type: "button", onclick: stopVoice }, "End")),
      h("div", { class: "voice-caps" }, voice.captions.length ? voice.captions.map((c) => h("div", { class: `cap ${c.who === "You" ? "you" : "bot"}` }, h("b", {}, c.who + " "), c.text)) : h("div", { class: "note-line" }, "Listening… ask about any well, or say a correction. Same planner and tools as the chat.")), input);
  };
  fab.onclick = () => (voice.state === "off" ? startVoice(state.userId) : stopVoice());
  onVoice((e) => { if (e.type === "error") alert("Voice unavailable: " + e.message); draw(); });
  draw(); return h("div", { class: "voice-dock" }, panel, fab);
}

onActive(() => (route() === "copilot" ? render() : go("copilot")));   // opening / creating a chat shows it

function render() {
  useUser(state.userId);
  if (route() === "copilot" && state.params?.prefill) freshIfUsed();
  const view = h("main", { class: "view", id: "view" });
  clear(app).append(sidebar(), view, dock());
  const v = route(), user = me(), prefill = state.params?.prefill; state.params = null;
  const nav = { wiki: (kind, id) => { location.hash = `#/wiki/${kind}/${id}`; }, copilot: (q) => go("copilot", { prefill: q }) };
  if (v === "copilot") mountCopilot(view, { user, prefill });
  else if (v === "wiki") mountWiki(view, { sub: parts().slice(1), nav });
  else if (v === "audit") mountAudit(view, { sub: parts().slice(1) });
  else if (v === "architecture") mountArchitecture(view, { sub: parts().slice(1) });
  else if (v === "qa") mountQA(view);
  else if (v === "report") mountReport(view, { user });
  else if (v === "judges") mountScorecard(view, { nav });
  else if (v === "knowledge") mountKnowledge(view);
  else mountOverview(view, { user, ask: (q) => go("copilot", { prefill: q }) });
}

applyTheme();
window.addEventListener("hashchange", render);
api.users().then((u) => { state.users = u; render(); }).catch((e) => { app.textContent = `Backend not reachable: ${e.message}`; });
