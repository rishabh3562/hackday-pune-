// Voice session (singleton): join a LiveKit room where the Gemini Live agent (voice/agent.py) talks to you and answers through the SAME copilot backend
// (/api/ask: same planner, same 34 tools, same memory). The dock (main.js) shows state and live captions; results are queued for the chat thread.
const SRC = "https://cdn.jsdelivr.net/npm/livekit-client@2.15.0/dist/livekit-client.umd.min.js";
const loadClient = () => window.LivekitClient ? Promise.resolve() : new Promise((ok, no) => { const s = document.createElement("script"); s.src = SRC; s.onload = ok; s.onerror = () => no(new Error("could not load livekit-client")); document.head.append(s); });

export const voice = { room: null, state: "off", captions: [], pending: [], userId: null };
const bus = new EventTarget();
export const onVoice = (fn) => { const h = (e) => fn(e.detail); bus.addEventListener("voice", h); return () => bus.removeEventListener("voice", h); };
const emit = (type, data = {}) => bus.dispatchEvent(new CustomEvent("voice", { detail: { type, ...data } }));
const setState = (s) => { voice.state = s; emit("state", { state: s }); };
const caption = (who, text, id) => {
  let c = voice.captions.find((x) => x.id === id);
  if (c) c.text = text; else { c = { who, text, id }; voice.captions.push(c); voice.captions = voice.captions.slice(-8); }
  emit("caption");
};

export async function startVoice(userId) {
  if (voice.room) return;
  setState("connecting"); voice.userId = userId; voice.captions = [];
  try {
    await loadClient(); const L = window.LivekitClient;
    const t = await fetch("/api/voice/token", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ user_id: userId }) }).then((r) => r.json());
    if (t.error) throw new Error(t.error);
    const room = new L.Room({ adaptiveStream: true, dynacast: true }), audio = [];
    room.on(L.RoomEvent.TrackSubscribed, (track) => { if (track.kind === "audio") { const el = track.attach(); el.style.display = "none"; document.body.append(el); audio.push(el); } });
    room.on(L.RoomEvent.DataReceived, (payload, _p, _k, topic) => { if (topic === "copilot-result") { const r = JSON.parse(new TextDecoder().decode(payload)); voice.pending.push(r); emit("result", { result: r }); } });
    room.on(L.RoomEvent.ActiveSpeakersChanged, (sp) => setState(sp.some((s) => !s.isLocal) ? "speaking" : sp.some((s) => s.isLocal) ? "listening" : "idle"));
    room.on(L.RoomEvent.Disconnected, () => { audio.forEach((a) => a.remove()); voice.room = null; setState("off"); });
    try {   // full results come as a text stream (too big for a data packet)
      room.registerTextStreamHandler("copilot-result", async (reader) => { try { const r = JSON.parse(await reader.readAll()); voice.pending.push(r); emit("result", { result: r }); } catch { /* ignore */ } });
    } catch { /* ignore */ }
    try {   // live captions for both sides (LiveKit publishes transcriptions on a text stream)
      // One caption line per transcription SEGMENT (attribute lk.segment_id): LiveKit sends a new text stream for every interim/final update of the same segment,
      // so keying by the stream id (as before) produced one duplicate line per update. Within a stream the agent sends deltas; a user stream carries the whole text so far.
      room.registerTextStreamHandler("lk.transcription", async (reader, info) => {
        const a = reader.info?.attributes || {}, who = String(info.identity || "").startsWith("user-") ? "You" : "Voice";
        const id = a["lk.segment_id"] || reader.info?.id || String(Math.random()); let text = "";
        for await (const chunk of reader) { text += chunk; caption(who, text, id); }
      });
    } catch { /* captions are a bonus */ }
    await room.connect(t.url, t.token); await room.localParticipant.setMicrophoneEnabled(true);
    voice.room = room; setState("idle");
  } catch (e) { voice.room = null; setState("off"); emit("error", { message: String(e.message || e) }); }
}
export const stopVoice = () => voice.room?.disconnect();
export const sendVoiceText = (text) => voice.room?.localParticipant.sendText(text, { topic: "lk.chat" });
