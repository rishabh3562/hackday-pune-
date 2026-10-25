"""Router-only benchmark: does the model pick the right tool/kind and key args? (writer skipped, 1 LLM call per question)
  COPILOT_BACKEND=gemma|(default gemini) .venv/bin/python -u tests/bench_router.py"""
import os, sys
os.environ.setdefault("COPILOT_CLARIFY", "auto")
sys.path.insert(0, ".")
os.environ["NO_WRITER"] = "1"
os.environ["TRACE_FILE"] = "/dev/null"
for l in open(".env"):
    k, v = l.strip().split("=", 1); os.environ.setdefault(k, v)
from copilot.data import Dataset
from copilot.memory import Memory
from copilot.tools import Engine
from copilot.agent import Agent
a = Agent(Engine(Dataset("data/repo/sample-data"), Memory(":memory:")))
# (question, expected kind, expected tool, {arg: expected value or None=just present})
C = [
 ("Is WELL-0001 producing oil right now? When was it last inspected, and by whom?", "query", "well_status", {"well": "WELL-0001"}),
 ("Which wells in Northeast Block 8 are not producing oil right now, and why? Show them in a table.", "query", "wells_not_producing", {"area": "Northeast Block 8"}),
 ("Show a line chart of WELL-0001's wellhead temperature against air temperature for the last 13 weeks, and mark when it was not producing oil.", "query", "timeseries", {"well": "WELL-0001", "weeks": 13}),
 ("How many oil spills has WELL-0001 had in the last 4 years, and how much oil in total? List them in a table.", "query", "spills", {"well": "WELL-0001", "months": 48}),
 ("How many days was WELL-0001 down in 2025?", "query", "downtime", {"well": "WELL-0001", "year": 2025}),
 ("Which 3 wells in Northeast Block 7 had the most downtime in the last 4 months? Show a bar chart.", "query", "downtime", {"area": "Northeast Block 7", "months": 4, "top_n": 3}),
 ("Show on a map every well in Northeast Block 8 with a real spill in the last 90 days.", "query", "spills", {"area": "Northeast Block 8", "days": 90}),
 ("Show a heatmap of 2026 spills by geographic area and month.", "query", "spills", {"year": 2026, "group_by": "area_month"}),
 ("Which rules has WELL-0001 broken in the last 12 months, and what is still open?", "query", "compliance", {"well": "WELL-0001"}),
 ("In Southwest Block 24, which spills in the last 90 days were not contained within the SOP time limit?", "query", "spills_over_containment", {"area": "Southwest Block 24", "days": 90}),
 ("The 15 Oct reading for WELL-0164 is wrong. The handheld thermal gun used in that inspection was faulty; the field crew re-measured the wellhead at 41.0 °C.", "correct_raw", None, {"well": "WELL-0164", "value": 41.0}),
 ("The AI estimated the 24 Sep spill at WELL-0151 as 4.5 bbl. The field crew measured 5.4 bbl.", "correct_ai", None, {"well": "WELL-0151", "value": 5.4}),
 ("Which wells in Northeast Block 7 need a root-cause analysis on their pump jack?", "query", "rca_candidates", {"area": "Northeast Block 7", "equipment": "pump_jack"}),
 ("Note for all T350 wells: our team now wants a pump jack root-cause analysis after 2 repairs, not 3.", "rule", None, {"well_type": "T350", "value": 2}),
 ("FYI for everyone: WELL-0007 will be shut in from 17 Oct for a 10-day planned workover.", "note", None, {"well": "WELL-0007"}),
 ("WELL-0175 is running fine.", "note", None, {"well": "WELL-0175"}),
 ("Was the 20 Aug spill at WELL-0101 real oil?", "query", "spill_check", {"well": "WELL-0101"}),
 ("Which spills in Northeast Block 8 in the last 90 days needed a report to the regulator?", "query", "spills", {"area": "Northeast Block 8", "reportable_only": True}),
 ("Which wells in Southwest Block 24 are 'high failed' wells: two or more corrective repairs in the last 12 months?", "query", "repair_summary", {"group_by": "well", "min_count": 2}),
 ("Compare total repair spend by area for 2025 as a bar chart.", "query", "repair_summary", {"group_by": "area", "year": 2025}),
 ("Which wells breached the 14-day inspection rule (RC-01) in 2026?", "query", "inspection_gaps", {"year": 2026}),
 ("What is the total of open regulator fines across the field and which wells carry them?", "query", "fines", {}),
 ("Show monthly downtime days for Northeast Block 7 in 2026 as a line chart.", "query", "downtime_trend", {"area": "Northeast Block 7", "year": 2026}),
 ("What is the mean time between corrective repairs for T200 versus T350 wells? Bar chart please.", "query", "mtbf", {}),
 ("What was the single most expensive repair in 2026?", "query", "top_repairs", {"year": 2026}),
 ("Which technicians did the most corrective repairs in Northeast Block 8 in the last 12 months? Top 3.", "query", "repair_summary", {"group_by": "technician", "top_n": 3}),
 ("Which wells in Southwest Block 23 have a recorded status that disagrees with their latest inspection?", "query", "stale_status", {"area": "Southwest Block 23"}),
 ("In the last 12 months, how many real spills were found by drone versus manual inspection?", "query", "spill_breakdown", {"by": "method"}),
 ("Which repairs are currently in progress across the field?", "query", "open_repairs_all", {}),
 ("Which wells have been down for more than 14 consecutive days right now and must be reported to the supervisor (RC-03)?", "query", "consecutive_down", {}),
 ("Which wells had repeat failures in 2026: a corrective repair on the same equipment within 90 days of the last one?", "query", "repeat_failures", {"days": 90, "year": 2026}),
 ("Of the reportable spills in the last 12 months, how many were reported late or never, and what fines are still open?", "query", "spill_response_summary", {"months": 12}),
 ("How much did repairs triggered by spills cost in 2026, by area?", "query", "spill_repair_cost", {"year": 2026}),
 ("Which areas still lack the annual flowline integrity test (RC-02) for 2026, and how many wells in each?", "query", "flowline_tests", {"year": 2026}),
 ("In 2025, where did we see hot wellheads above 45 °C that were still not producing oil? Count by area.", "query", "hot_false_alarms", {"year": 2025}),
 ("Which wells are not producing right now and also had a corrective repair in the last 90 days?", "query", "down_with_recent_repair", {"days": 90}),
 ("Which wells stopped producing at their latest inspection after producing at the one before?", "query", "newly_stopped", {}),
 ("How many 2026 spill detections were removed by corrections, and how many real spills remain?", "query", "correction_impact", {"year": 2026}),
 ("For the 5 wells with the most downtime in the last 12 months, what did repairs cost and what is the cost per downtime day?", "query", "downtime_cost", {"months": 12, "top_n": 5}),
 ("Show the quarterly trend of reportable spills (5 bbl or more) since 2023.", "query", "spill_breakdown", {"by": "quarter"}),
]
ok_tool = ok_args = 0
fails = []
for i, (q, kind, tool, args) in enumerate(C, 1):
    try:
        o = a.ask("U-201", f"b{i}", q); p = o["plan"]
    except Exception as ex:  # noqa: BLE001
        p = {"kind": "ERR", "tool": str(ex)[:60]}
    pk = p.get("kind"); pt = p.get("tool") or (p.get("calls") or [{}])[0].get("tool")
    pa = p.get("args") or (p.get("calls") or [{}])[0].get("args") or {}
    pa = {**p, **pa}
    t_ok = pk == kind and (tool is None or pt == tool)
    a_ok = t_ok and all(str(pa.get(k)).lower() == str(v).lower() or (k == "value" and abs(float(pa.get(k, -1)) - float(v)) < 1e-6) for k, v in args.items())
    ok_tool += t_ok; ok_args += a_ok
    if not a_ok:
        fails.append((i, q[:70], kind, tool, args, {k: pa.get(k) for k in list(args) + ["tool"]}))
    print(i, "OK " if a_ok else ("TOOL" if t_ok else "FAIL"), pt or pk, flush=True)
print(f"backend={os.environ.get('COPILOT_BACKEND','gemini')}  tool/kind accuracy {ok_tool}/{len(C)}  tool+args accuracy {ok_args}/{len(C)}")
for f in fails:
    print("  miss:", f)
sys.path.insert(0, "tests"); import _results; _results.save("router-" + os.environ.get("COPILOT_BACKEND", "gemini"), [{"id": str(i), "desc": c[0][:90], "ok": i not in {f[0] for f in fails}} for i, c in enumerate(C, 1)], {"tool_kind_accuracy": ok_tool, "tool_args_accuracy": ok_args})
