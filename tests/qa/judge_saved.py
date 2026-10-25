"""Judge the answers ALREADY recorded by the extra and design-review suites (no agent re-run), so the LLM judge covers every scenario, not just the 18 given ones.
  .venv/bin/python tests/qa/judge_saved.py        -> adds a "judge" entry to each item in tests/results/{extra,design-review}.json
extra: expected = the independent pandas ground truth.  design-review: expected = the behaviour the scenario is meant to show; the judge reads the whole dialogue."""
import json, os, sys, time
from concurrent.futures import ThreadPoolExecutor
os.environ["TRACE_FILE"] = "/dev/null"
for l in open(".env"):
    k, v = l.strip().split("=", 1); os.environ.setdefault(k, v)
sys.path.insert(0, "."); sys.path.insert(0, "tests/qa")
import copilot.agent as A
from rubric import RUBRIC
JUDGE = os.environ.get("JUDGE_MODEL", "gemini-2.5-pro")

def grade(prompt):
    prev = A.VERTEX_MODEL; A.VERTEX_MODEL = JUDGE
    try:
        for _ in range(2):
            try: return A.parse_json(A.call_llm([{"role": "system", "content": RUBRIC}, {"role": "user", "content": prompt}], 600, json_mode=True, label="judge"))
            except Exception as ex: err = str(ex)[:120]  # noqa: BLE001
        return {"error": err}
    finally: A.VERTEX_MODEL = prev

jobs = []
for suite in ("extra", "design-review"):
    path = f"tests/results/{suite}.json"; d = json.load(open(path))
    for it in d["items"]:
        if suite == "extra" and it.get("actual"):
            jobs.append((path, it["id"], f"QUESTION: {it['question']}\nEXPECTED FACTS (independent ground truth): {it['expected']}\nANSWER TEXT: {it['actual']}\nVISUALS ALSO SHOWN: {it.get('visual')}"))
        elif suite == "design-review" and it.get("answers"):
            dlg = "\n".join(f"{a['user']}: {a['q']}\nCOPILOT: {a['a']}" for a in it["answers"])
            jobs.append((path, it["id"], f"QUESTION: this is a multi-step scenario that must show this behaviour: {it['desc']}\nEXPECTED FACTS: the dialogue demonstrates that behaviour correctly and honestly\nANSWER TEXT (whole dialogue):\n{dlg}"))
print(len(jobs), "answers to judge with", JUDGE, flush=True)
with ThreadPoolExecutor(3) as ex: results = list(ex.map(lambda j: grade(j[2]), jobs))
by = {}
for (path, iid, _), r in zip(jobs, results): by.setdefault(path, {})[iid] = r
for path, m in by.items():
    d = json.load(open(path))
    for it in d["items"]:
        if it["id"] in m: it["judge"] = m[it["id"]]
    d["judge_model"], d["judged_at"] = JUDGE, time.strftime("%Y-%m-%d %H:%M")
    json.dump(d, open(path, "w"), indent=1)
ok = sum(1 for r in results if r.get("verdict") == "pass"); print("judged", len(results), "pass", ok, "errors", sum(1 for r in results if "error" in r))
