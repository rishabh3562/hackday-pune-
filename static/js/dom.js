// Tiny DOM helpers. h() never uses innerHTML, so model/user text can't inject markup.
export function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "aria-pressed" || k === "aria-current") el.setAttribute(k, String(v));
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat(Infinity)) if (kid != null && kid !== false) el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  return el;
}
export const clear = (el) => { el.replaceChildren(); return el; };
export const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
export const initials = (name = "") => name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
// Replace an element's children; null/false are skipped (Element.append would print "null").
export const mount = (el, ...kids) => { el.replaceChildren(...kids.flat(Infinity).filter((k) => k != null && k !== false)); return el; };
