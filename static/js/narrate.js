// Read-aloud for the TEXT part of an answer with the browser's built-in speech synthesis, highlighting the word being spoken.
import { h } from "./dom.js";

const synth = window.speechSynthesis;
let current = null;                                    // {utter, el, btn}
export const supported = () => !!synth && typeof SpeechSynthesisUtterance !== "undefined";

function stop() {
  if (!current) return;
  current.utter.onend = current.utter.onerror = null;
  synth.cancel(); current.el.querySelectorAll(".w.speaking").forEach((w) => w.classList.remove("speaking"));
  current.btn.textContent = "🔊 Listen"; current.btn.setAttribute("aria-pressed", "false"); current = null;
}

function speak(el, btn, rate) {
  stop();
  const spans = [...el.querySelectorAll(".w")]; let pos = 0, text = "";
  const starts = spans.map((s) => { const start = text.length; text += s.textContent + " "; pos = text.length; return start; });
  const u = new SpeechSynthesisUtterance(text.trim()); u.rate = rate(); u.lang = "en-US";
  let real = false, timer = null, k = 0;                       // some voices never fire word boundaries: fall back to a timed highlight
  const mark = (i) => { spans.forEach((x) => x.classList.remove("speaking")); if (i >= 0 && spans[i]) { spans[i].classList.add("speaking"); spans[i].scrollIntoView({ block: "nearest", behavior: "smooth" }); } };
  u.onstart = () => { setTimeout(() => { if (!real && current?.utter === u) timer = setInterval(() => { if (k >= spans.length) return clearInterval(timer); mark(k++); }, 60000 / (165 * u.rate)); }, 900); };
  u.onboundary = (e) => {
    if (e.name && e.name !== "word") return;
    real = true; clearInterval(timer);
    let i = starts.findIndex((s, k) => e.charIndex >= s && (k === starts.length - 1 || e.charIndex < starts[k + 1]));
    spans.forEach((s) => s.classList.remove("speaking")); if (i >= 0) { spans[i].classList.add("speaking"); spans[i].scrollIntoView({ block: "nearest", behavior: "smooth" }); }
  };
  u.onend = u.onerror = () => { clearInterval(timer); if (current?.utter === u) stop(); };
  current = { utter: u, el, btn }; btn.textContent = "⏹ Stop"; btn.setAttribute("aria-pressed", "true"); synth.speak(u);
}

// A small control row: Listen/Stop + speed. `el` is the rendered text element (from text.js).
export function narrateControls(el, auto = false) {
  if (!supported()) return null;
  const speed = h("select", { class: "select tiny", "aria-label": "Reading speed" }, [["0.9", "0.9×"], ["1", "1×"], ["1.2", "1.2×"], ["1.5", "1.5×"]].map(([v, l]) => h("option", { value: v, selected: v === "1" }, l)));
  const btn = h("button", { class: "btn small", type: "button", "aria-pressed": "false" }, "🔊 Listen");
  btn.onclick = () => (current?.btn === btn ? stop() : speak(el, btn, () => Number(speed.value)));
  if (auto) setTimeout(() => speak(el, btn, () => Number(speed.value)), 150);
  return h("div", { class: "msg-meta" }, btn, speed);
}
export const stopNarration = stop;
