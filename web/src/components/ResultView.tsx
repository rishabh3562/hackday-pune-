"use client";
// Thin React host for the shared, framework-free block renderer served by the backend (static/js/blocks.js),
// so the plain UI and this CopilotKit UI show exactly the same visualizations.
import { createContext, useContext, useEffect, useRef } from "react";

export const API = process.env.NEXT_PUBLIC_API || "http://localhost:8000";
// the dynamic import is hidden from the bundler on purpose: the module lives on the backend origin
const importModule = (url: string): Promise<any> => new Function("u", "return import(u)")(url);
let blocksModule: Promise<any> | null = null;
const loadBlocks = () => (blocksModule ??= importModule(`${API}/static/js/blocks.js`));

// lets the page send a reply as the next user message (used by the clarify option buttons)
export const PickContext = createContext<(text: string) => void>(() => {});

type Spec = { visual?: string; blocks?: any[]; options?: string[]; citations?: string[] };

export function ResultView({ spec }: { spec: Spec }) {
  const host = useRef<HTMLDivElement>(null);
  const pick = useContext(PickContext);
  useEffect(() => {
    if (!spec?.blocks?.length || !host.current) return;
    let alive = true;
    loadBlocks().then((m) => { if (alive && host.current) host.current.replaceChildren(m.renderBlocks(spec.blocks)); });
    return () => { alive = false; };
  }, [spec]);
  if (!spec) return null;
  if (spec.visual === "clarify")
    return (
      <div className="options">
        {(spec.options || []).map((o) => <button key={o} type="button" className="option" onClick={() => pick(o)}>{o}</button>)}
        <span className="small mute" style={{ alignSelf: "center" }}>…or type your own answer below.</span>
      </div>
    );
  const evidence = Array.from(new Set(spec.citations || [])).slice(0, 40);
  return (
    <div className="stack">
      <div ref={host} />
      {evidence.length > 0 && <div><span className="small mute">Evidence: </span>{evidence.map((c) => <span key={c} className="chip">{c}</span>)}</div>}
    </div>
  );
}
