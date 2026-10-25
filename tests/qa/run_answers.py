"""Real answers for the 26 given-scenario questions, with expected facts, optionally graded by an LLM judge.
  .venv/bin/python tests/qa/run_answers.py [--judge] [roots]     -> tests/results/answers.json
The judge (default gemini-2.5-pro, different from the writer) scores correctness, grounding, completeness, honesty, clarity (1-5)."""
import json, os, sys
os.environ.setdefault("COPILOT_CLARIFY", "auto"); os.environ["TRACE_FILE"] = "/dev/null"
sys.path.insert(0, ".")
for l in open(".env"):
    k, v = l.strip().split("=", 1); os.environ.setdefault(k, v)
from copilot.data import Dataset
from copilot.memory import Memory
from copilot.agent import Agent, Engine, call_llm, parse_json
sys.path.insert(0, "tests/qa"); from expected import EXPECTED
sys.path.insert(0, "tests"); import _results
judge = "--judge" in sys.argv
roots = ([a for a in sys.argv[1:] if not a.startswith("--")] or ["data/repo/sample-data"])[0].split(",")
ds = Dataset(*roots); agent = Agent(Engine(ds, Memory(":memory:")))
ids = {u["name"].lower(): u["user_id"] for u in ds.users}
JUDGE = os.environ.get("JUDGE_MODEL", "gemini-2.5-pro")
from rubric import RUBRIC
def grade(q, exp, ans, shown=""):
    import copilot.agent as A
    prev = A.VERTEX_MODEL; A.VERTEX_MODEL = JUDGE          # judge with a different (stronger) model, then switch back
    try: return parse_json(call_llm([{"role": "system", "content": RUBRIC}, {"role": "user", "content": f"QUESTION: {q}\nEXPECTED FACTS: {exp}\nANSWER TEXT: {ans}\nVISUALS AND DATA ALSO SHOWN TO THE USER (judge these as part of the answer): {shown}"}], 600, json_mode=True))
    except Exception as ex:  # noqa: BLE001
        return {"error": str(ex)[:120]}
    finally: A.VERTEX_MODEL = prev
items, chat, n = [], 1, 0
for line in open("tests/final_questions_sample.txt"):
    line = line.strip()
    if not line or line.startswith("#"): continue
    if line.startswith("---"): chat += 1; continue
    name, q = line.split(":", 1); uid = ids.get(name.strip().lower(), name.strip()); sid, exp = EXPECTED[n]; n += 1
    o = agent.ask(uid, f"qa-{chat}-{uid}", q.strip())
    it = {"id": sid, "suite": "given", "user": name.strip(), "question": q.strip(), "expected": exp, "actual": o["text"], "tool": o["plan"].get("tool") or o["plan"].get("kind"),
          "visual": o.get("visual"), "blocks": [b["type"] for b in o.get("blocks", [])], "citations": list(dict.fromkeys(o.get("citations", [])))[:30],
          "rows_preview": (o.get("rows") or [])[:6]}
    shown = f"blocks={it['blocks']}; first rows={json.dumps(it['rows_preview'], default=str)[:1500]}; " + "; ".join(f"{b['type']}:{b.get('title') or ''}" + (f" labels={b['labels']} values={[s['values'] for s in b.get('series', [])]}" if b['type'] in ('bar', 'line') else "") + (f" pins={[p['label'] for p in b['pins']]}" if b['type'] == 'map' else "") + (f" rows={b['rowLabels']} values={b['values']}" if b['type'] == 'heatmap' else "") for b in o.get("blocks", []))[:3500]
    if judge: it["judge"] = grade(q.strip(), exp, o["text"], shown)
    items.append(it); print(sid, it.get("judge", {}).get("verdict", ""), flush=True)
_results.save("answers", [{**i, "ok": (i.get("judge", {}).get("verdict") == "pass") if judge else True, "desc": i["question"]} for i in items], {"judge_model": JUDGE if judge else None})
