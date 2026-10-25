// One place that talks to the backend.
const json = async (res) => { if (!res.ok) throw new Error(`${res.status} ${res.statusText}`); return res.json(); };
export const api = {
  users: () => fetch("/api/users").then(json),
  briefing: () => fetch("/api/briefing").then(json),
  facts: () => fetch("/api/facts").then(json),
  revoke: (id) => fetch(`/api/facts/${id}/revoke`, { method: "POST" }).then(json),
  wikiIndex: () => fetch("/api/wiki").then(json),
  wiki: (kind, id) => fetch(`/api/wiki/${kind}/${id}`).then(json),
  audit: (what) => fetch(`/api/audit/${what}`).then(json),
  vectors: () => fetch("/api/vectors").then(json),
  vquery: (q) => fetch(`/api/vectors/query?q=${encodeURIComponent(q)}&k=8`).then(json),
  vbrowse: (kind, q) => fetch(`/api/vectors/browse?kind=${encodeURIComponent(kind)}&q=${encodeURIComponent(q)}&limit=25`).then(json),
  ask: (user_id, chat_id, text, mode) => fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ user_id, chat_id, text, mode }) }).then(json),
  chats: (uid) => fetch(`/api/chats?user_id=${encodeURIComponent(uid)}`).then(json),
  chat: (uid, id) => fetch(`/api/chats/${encodeURIComponent(id)}?user_id=${encodeURIComponent(uid)}`).then(json),
  deleteChat: (uid, id) => fetch(`/api/chats/${encodeURIComponent(id)}?user_id=${encodeURIComponent(uid)}`, { method: "DELETE" }).then(json),
  renameChat: (uid, id, title) => fetch(`/api/chats/${encodeURIComponent(id)}?user_id=${encodeURIComponent(uid)}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title }) }).then(json),
};
