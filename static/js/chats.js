// Chat sessions: per-user list, the active chat (remembered in localStorage), in-memory threads keyed by (user, chat), and the sidebar panel.
import { h, mount } from "./dom.js";
import { api } from "./api.js";

const ls = { get: (k) => { try { return localStorage.getItem(k); } catch { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch { /* private mode */ } } };
const newId = () => `c${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
const threads = new Map();                 // `${uid}|${chatId}` -> {chatId, messages[], busy, loaded}; answers are written to THEIR thread, never "the current one"
const S = { uid: null, list: [], active: null, loading: false };
const subs = new Set(), activeSubs = new Set();
const emit = () => subs.forEach((f) => f());

export const thread = (uid, chatId) => { const k = `${uid}|${chatId}`; if (!threads.has(k)) threads.set(k, { chatId, messages: [], busy: false, loaded: false }); return threads.get(k); };
export const activeChat = () => S.active;
export const onActive = (f) => activeSubs.add(f);

export function setActive(id, silent = false) {
  S.active = id; ls.set(`chat:${S.uid}`, id); emit();
  if (!silent) activeSubs.forEach((f) => f());
}
export function newChat(silent = false) { setActive(newId(), silent); }
// Start from a clean chat unless the active one is still empty (used when a prefilled question arrives from another page).
export function freshIfUsed() { const t = thread(S.uid, S.active); if (t.messages.length || S.list.some((c) => c.id === S.active)) newChat(true); }

export async function refreshChats() {
  const uid = S.uid;
  try { const l = await api.chats(uid); if (S.uid === uid) { S.list = l; emit(); } } catch { /* offline: keep what we have */ }
}
export function useUser(uid) {             // call on every render; reloads only when the user actually changes
  if (S.uid === uid) return;
  S.uid = uid; S.list = []; S.active = ls.get(`chat:${uid}`) || newId(); ls.set(`chat:${uid}`, S.active);
  refreshChats();
}
export async function deleteChat(id) {
  const uid = S.uid; await api.deleteChat(uid, id); threads.delete(`${uid}|${id}`);
  S.list = S.list.filter((c) => c.id !== id);
  if (S.active === id) newChat(); else emit();
  refreshChats();
}

// Saved turns -> UI messages (the answer JSON was stored with the assistant turn, so blocks re-render).
export async function loadHistory(uid, t) {
  if (t.loaded || t.loading) return;
  t.loading = true;
  try {
    const { turns } = await api.chat(uid, t.chatId);
    if (!t.messages.length) t.messages = turns.map((x) => x.role === "user" ? { role: "user", text: x.text } : { role: "bot", text: x.text, spec: x.payload || { text: x.text, visual: "text", rows: [], citations: [] } });
    t.loaded = true;
  } catch { /* leave empty; the next open retries */ }
  t.loading = false; t.redraw?.();
}

const dayOf = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
function group(ts) {
  const d = new Date(ts), today = dayOf(new Date()), x = dayOf(d), n = Math.round((today - x) / 864e5);
  return n <= 0 ? "Today" : n === 1 ? "Yesterday" : n < 8 ? "Previous 7 days" : "Earlier";
}

// The accordion body under the "Copilot" nav item. Redraws itself when the list changes; no full-app render needed.
export function chatPanel() {
  const root = h("div", { class: "chat-sub", id: "chat-sub", role: "region", "aria-label": "Chats" });
  const draw = () => {
    if (!root.isConnected && root.dataset.born) { subs.delete(draw); return; }
    root.dataset.born = "1";
    const list = S.list.some((c) => c.id === S.active) ? S.list : [{ id: S.active, title: "New chat", last_ts: new Date().toISOString(), draft: true }, ...S.list];
    const groups = {}; list.forEach((c) => (groups[group(c.last_ts)] ||= []).push(c));
    mount(root,
      h("button", { class: "btn small chat-new", type: "button", onclick: () => newChat() }, "＋ New chat"),
      ...["Today", "Yesterday", "Previous 7 days", "Earlier"].filter((g) => groups[g]).map((g) => h("div", { class: "chat-group" },
        h("div", { class: "chat-group-title" }, g),
        groups[g].map((c) => h("div", { class: `chat-item${c.id === S.active ? " active" : ""}` },
          h("button", { class: "chat-open", type: "button", title: c.title, "aria-current": c.id === S.active ? "true" : null, onclick: () => setActive(c.id) }, c.title),
          c.draft ? null : h("span", { class: "chat-actions" },
            h("button", { class: "chat-act", type: "button", title: "Rename chat", "aria-label": `Rename chat ${c.title}`, onclick: async () => { const v = prompt("Rename chat", c.title); if (v && v.trim()) { await api.renameChat(S.uid, c.id, v.trim()); refreshChats(); } } }, "✎"),
            h("button", { class: "chat-act", type: "button", title: "Delete chat", "aria-label": `Delete chat ${c.title}`, onclick: () => { if (confirm("Delete this chat?")) deleteChat(c.id); } }, "🗑"))))))
    );
  };
  subs.add(draw); draw(); return root;
}
