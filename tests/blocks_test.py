"""Multi-visualization composition (no LLM): each answer gets several block types, JSON-safe, with sensible content.
Run: .venv/bin/python tests/blocks_test.py"""
import json, os, sys
os.environ["NO_WRITER"] = "1"; os.environ["TRACE_FILE"] = "/dev/null"; os.environ.setdefault("COPILOT_CLARIFY", "auto")
sys.path.insert(0, ".")
from copilot.data import Dataset
from copilot.memory import Memory
from copilot.agent import Agent, Engine
from copilot import blocks
ds = Dataset("data/repo/sample-data"); e = Engine(ds, Memory(":memory:")); a = Agent(e)
fails = 0
ITEMS = []
def check(name, ok, info=""):
    global fails; fails += not ok; ITEMS.append({"id": name.split()[0], "desc": name, "ok": bool(ok)}); print(("PASS " if ok else "FAIL ") + name, "" if ok else info)
T = lambda b: [x["type"] for x in b]
def build(tool, res): b = blocks.build(e, tool, res); json.dumps(b); return b

b = build("well_status", e.well_status("WELL-0001"))
check("V1 well status: card + callouts + trend + scatter + timeline + map (>=6 distinct types)", len(set(T(b))) >= 6 and {"status", "callout", "line", "scatter", "timeline", "map"} <= set(T(b)), T(b))
b = build("wells_not_producing", e.wells_not_producing("Northeast Block 8"))
check("V2 area list: KPIs + table + callout + bar + map", {"kpis", "table", "callout", "bar", "map"} <= set(T(b)) and b[0]["items"][0]["value"] == 4, T(b))
b = build("downtime", e.downtime(area="Northeast Block 7", months=4, top_n=3))
check("V3 downtime ranking: KPIs + bar + donut + table; bar has the 3 expected wells", {"kpis", "bar", "donut", "table"} <= set(T(b)) and sorted(next(x for x in b if x["type"] == "bar")["labels"]) == ["WELL-0107", "WELL-0121", "WELL-0138"], T(b))
b = build("spills", e.spills(area="Northeast Block 8", days=90))
check("V4 spills: KPIs + table + map + donut + bar, 4 pins", {"kpis", "table", "map", "donut", "bar"} <= set(T(b)) and len(next(x for x in b if x["type"] == "map")["pins"]) == 4, T(b))
b = build("spills", e.spills(year=2026, group_by="area_month"))
hm = next(x for x in b if x["type"] == "heatmap")
check("V5 heatmap answer: KPIs + heatmap + bar + line; totals match Q8", sum(map(sum, hm["values"])) == 141 and {"kpis", "heatmap", "bar", "line"} <= set(T(b)), (T(b), sum(map(sum, hm["values"]))))
b = build("compliance", e.compliance(well="WELL-0001", months=12))
check("V6 compliance: KPIs + breaches table + open actions table + donut", T(b).count("table") == 2 and "donut" in T(b) and b[0]["items"][0]["value"] == 4, T(b))
b = build("trace", e.trace("INS-0001-0185"))
check("V7 trace: timeline + table", T(b) == ["timeline", "table"] and len(b[0]["events"]) >= 5, T(b))
b = build("timeseries", e.timeseries("WELL-0001", 13))
check("V8 trend: KPIs + line (red points flagged) + callout + scatter + table", {"kpis", "line", "callout", "scatter", "table"} <= set(T(b)) and b[1]["flags"].count(False) == 2, T(b))
o = a.query({"calls": [{"tool": "well_status", "args": {"well": "WELL-0001"}}, {"tool": "downtime", "args": {"area": "Northeast Block 7", "months": 4, "top_n": 3}}]}, "U-201", "x", "c")
check("V9 compound question: blocks of BOTH parts in one response", {"status", "bar", "donut"} <= set(T(o["blocks"])) and len(o["blocks"]) >= 10, T(o["blocks"]))
o = a.ask("U-201", "r1", "Which 3 wells in Northeast Block 7 had the most downtime in the last 4 months? Show a bar chart.")
o2 = a.ask("U-201", "r1", "Show that as a table instead.")
check("V10 re-render: same data as a table, no re-query", o2["plan"].get("kind") == "rerender" and o2["blocks"][0]["type"] == "table", (o2["plan"], T(o2.get("blocks", []))))
print("FAILS:", fails)
sys.path.insert(0, "tests"); import _results; _results.save("blocks", ITEMS)
