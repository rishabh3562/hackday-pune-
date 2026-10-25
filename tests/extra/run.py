"""22 extra scenarios (11 medium M, 11 complex C). Questions go through the LLM agent; answers are checked against
independent pandas ground truth (truth.py). Run: .venv/bin/python -u tests/extra/run.py [ids]"""
import os, sys, io, contextlib
os.environ.setdefault("COPILOT_CLARIFY", "auto")
sys.path.insert(0, ".")
for l in open(".env"):
    k, v = l.strip().split("=", 1); os.environ[k] = v
with contextlib.redirect_stdout(io.StringIO()):
    sys.argv = [sys.argv[0]] + sys.argv[1:]
    import importlib.util
    spec = importlib.util.spec_from_file_location("truth", "tests/extra/truth.py"); truth = importlib.util.module_from_spec(spec)
    only = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else None
    sys.argv = [sys.argv[0]]; spec.loader.exec_module(truth)
from copilot.data import Dataset
from copilot.memory import Memory
from copilot.tools import Engine
from copilot.agent import Agent
a = Agent(Engine(Dataset("data/repo/sample-data"), Memory(":memory:")))
T = truth.out
col = lambda rows, k: [r[k] for r in rows]
def firstnum(r):
    return [v for k, v in r.items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
S = {
 "M1": ("Which wells in Southwest Block 24 are 'high failed' wells: two or more corrective repairs in the last 12 months?",
        lambda o: sorted(col(o["rows"], "Well")) == T["M1"]),
 "M2": ("Compare total repair spend by area for 2025 as a bar chart.",
        lambda o: {r["Area"]: r["Cost (USD)"] for r in o["rows"]} == T["M2"] and o["visual"] == "bar"),
 "M3": ("Which wells breached the 14-day inspection rule (RC-01) in 2026?",
        lambda o: sorted({r["Well"] for r in o["rows"]}) == T["M3"]),
 "M4": ("What is the total of open regulator fines across the field and which wells carry them?",
        lambda o: sorted({r["Well"] for r in o["rows"]}) == T["M4"]["wells"] and sum(r["Fine (USD)"] for r in o["rows"]) == T["M4"]["total"]),
 "M5": ("Show monthly downtime days for Northeast Block 7 in 2026 as a line chart.",
        lambda o: {int(r["Period"][-2:]): r["Downtime (days)"] for r in o["rows"]} == T["M5"] and o["visual"] == "line"),
 "M6": ("What is the mean time between corrective repairs for T200 versus T350 wells? Bar chart please.",
        lambda o: {r["Type"]: r["Mean days between corrective repairs"] for r in o["rows"]} == T["M6"]),
 "M7": ("What was the single most expensive repair in 2026?",
        lambda o: (o["rows"][0]["Repair"], o["rows"][0]["Cost (USD)"]) == T["M7"]),
 "M8": ("Which technicians did the most corrective repairs in Northeast Block 8 in the last 12 months? Top 3.",
        lambda o: [int(r["Repairs"]) for r in o["rows"][:3]] == list(T["M8"].values()) and all(k in r["Technician"] for r, k in zip(o["rows"][:3], T["M8"]))),
 "M9": ("Which wells in Southwest Block 23 have a recorded status that disagrees with their latest inspection?",
        lambda o: sorted(col(o["rows"], "Well")) == T["M9"]),
 "M10": ("In the last 12 months, how many real spills were found by drone versus manual inspection?",
         lambda o: {r["Method"]: r["Spills"] for r in o["rows"]} == T["M10"]),
 "M11": ("Which repairs are currently in progress across the field?",
         lambda o: sorted({r["Well"] for r in o["rows"]}) == T["M11"]),
 "C1": ("Which wells have been down for more than 14 consecutive days right now and must be reported to the supervisor (RC-03)?",
        lambda o: sorted(col(o["rows"], "Well")) == T["C1"]),
 "C2": ("Which wells had repeat failures in 2026: a corrective repair on the same equipment within 90 days of the last one?",
        lambda o: sorted(col(o["rows"], "Well")) == T["C2"]),
 "C3": ("Of the reportable spills in the last 12 months, how many were reported late or never, and what fines are still open?",
        lambda o: (len(o["rows"]), o.get("late_or_missing")) == (T["C3"]["reportable"], T["C3"]["late_or_missing"])),
 "C4": ("How much did repairs triggered by spills cost in 2026, by area?",
        lambda o: {r["Area"]: r["Cost (USD)"] for r in o["rows"]} == T["C4"]),
 "C5": ("Which areas still lack the annual flowline integrity test (RC-02) for 2026, and how many wells in each?",
        lambda o: {r["Area"]: r["Wells without test"] for r in o["rows"]} == T["C5"]),
 "C6": ("In 2025, where did we see hot wellheads above 45 °C that were still not producing oil? Count by area.",
        lambda o: {r["Area"]: r["Hot but not producing"] for r in o["rows"]} == T["C6"]),
 "C7": ("Which wells are not producing right now and also had a corrective repair in the last 90 days?",
        lambda o: sorted(col(o["rows"], "Well")) == T["C7"]),
 "C8": ("Which wells stopped producing at their latest inspection after producing at the one before?",
        lambda o: sorted(col(o["rows"], "Well")) == T["C8"]),
 "C9": ("How many 2026 spill detections were removed by corrections, and how many real spills remain?",
        lambda o: len(o["rows"]) == T["C9"]["corrected_out"]),
 "C10": ("For the 5 wells with the most downtime in the last 12 months, what did repairs cost and what is the cost per downtime day?",
         lambda o: {r["Well"]: (r["Downtime (days)"], r["Repair cost (USD)"]) for r in o["rows"]} == T["C10"]),
 "C11": ("Show the quarterly trend of reportable spills (5 bbl or more) since 2023.",
         lambda o: {r["Quarter"]: r["Spills"] for r in o["rows"]} == T["C11"]),
}
ok = 0
ITEMS = []
for k, (q, check) in S.items():
    if only and k not in only:
        continue
    o = a.ask("U-201", "x" + k, q)
    try:
        good = bool(check(o))
    except Exception as ex:  # noqa: BLE001
        good = False; o["text"] += f" [check error: {ex!r}]"
    ok += good
    ITEMS.append({"id": k, "desc": q, "ok": bool(good), "ms": 0, "tool": o["plan"].get("tool"), "question": q, "expected": str(T[k])[:600], "actual": o["text"], "visual": o.get("visual")})
    print(("PASS " if good else "FAIL ") + k, o["plan"].get("tool"), o["plan"].get("args"), o.get("visual"))
    if not good:
        print("   rows:", str(o.get("rows"))[:300]); print("   want:", str(T[k])[:300])
print("passed", ok, "of", len(S) if not only else len(only))
if not only:
    sys.path.insert(0, "tests"); import _results; _results.save("extra", ITEMS)
