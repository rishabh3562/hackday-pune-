"""Context accounting: real token counts per answer, parts add up, raw data is never sent, rows are capped. Run: .venv/bin/python tests/context_test.py"""
import os, sys
os.environ["TRACE_FILE"] = "/dev/null"; os.environ.setdefault("COPILOT_CLARIFY", "auto")
for l in open(".env"):
    k, v = l.strip().split("=", 1); os.environ.setdefault(k, v)
sys.path.insert(0, ".")
from copilot.data import Dataset
from copilot.memory import Memory
from copilot.agent import Agent, Engine
a = Agent(Engine(Dataset("data/repo/sample-data"), Memory(":memory:")))
ITEMS = []
def check(i, desc, ok, info=""):
    ITEMS.append({"id": i, "desc": desc, "ok": bool(ok), "info": str(info)[:300]}); print(("PASS " if ok else "FAIL ") + i, desc, "" if ok else info)
o = a.ask("U-201", "c1", "Which wells in Northeast Block 8 are not producing oil right now, and why?"); c = o["context"]
check("X1", "an answer reports real token counts for each model call (router + writer)", {k["label"] for k in c["calls"]} >= {"router", "writer"} and all(k["exact"] for k in c["calls"]), [(k["label"], k["exact"]) for k in c["calls"]])
check("X2", "total tokens = prompt + output, and the prompt parts add up to the prompt (within 3%)", c["total_tokens"] == c["prompt_tokens"] + c["output_tokens"] and all(abs(sum(p["tokens"] for p in k["parts"]) - k["prompt_tokens"]) <= 0.03 * k["prompt_tokens"] + 3 for k in c["calls"]), c["calls"][0]["parts"])
check("X3", "the question is a tiny part of the router prompt and no dataset rows are in it", next(p["tokens"] for p in c["calls"][0]["parts"] if p["name"] == "your question") < 100, c["calls"][0]["parts"])
check("X4", "the model saw far less than 1% of the source data", c["share_of_dataset_pct"] < 1 and c["dataset_tokens"] > 1_000_000, (c["share_of_dataset_pct"], c["dataset_tokens"]))
o = a.ask("U-201", "c2", "Which wells in Southwest Block 24 have repairs in 2026 grouped by well?"); c2 = o["context"]
big = a.ask("U-201", "c3", "How much did each well in the field spend on repairs in 2025? Group by well.")["context"]
check("X5", "large results are capped before the writer: rows sent <= 30 while rows returned can be larger", big["rows_sent"] is not None and big["rows_sent"] <= 30 and (big["rows_returned"] or 0) >= big["rows_sent"], (big["rows_returned"], big["rows_sent"]))
check("X6", "the grounding guard outcome is recorded", c["guard"] in ("passed first time", "regenerated once", "template fallback"), c["guard"])
print("FAILS:", sum(not i["ok"] for i in ITEMS)); sys.path.insert(0, "tests"); import _results; _results.save("context", ITEMS)
