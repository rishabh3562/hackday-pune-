"""Open-ended SQL tool: answers match independent pandas truth; the validator rejects anything that is not one read-only query; routing is last-resort only.
Run: .venv/bin/python tests/sql_test.py"""
import glob, json, os, sys
os.environ["TRACE_FILE"] = "/dev/null"; os.environ.setdefault("COPILOT_CLARIFY", "auto"); os.environ["NO_WRITER"] = "1"
for l in open(".env"):
    k, v = l.strip().split("=", 1); os.environ.setdefault(k, v)
sys.path.insert(0, ".")
import pandas as pd
from copilot.data import Dataset
from copilot.memory import Memory
from copilot.agent import Agent, Engine
from copilot import sqltool
R = "data/repo/sample-data"
J = lambda f: [json.loads(l) for p in sorted(glob.glob(f"{R}/assets/*/{f}")) for l in open(p) if l.strip()]
I = pd.DataFrame(J("inspections.jsonl")); I["ts"] = pd.to_datetime(I.inspected_at, utc=True)
M = pd.DataFrame(J("maintenance.jsonl")); M["ts"] = pd.to_datetime(M.started_at, utc=True); M["cost"] = M.cost_usd.map(lambda c: c["total"])
users = {u["user_id"]: u["name"] for u in json.load(open(f"{R}/fleet/users.json"))["users"]}
e = Engine(Dataset(R), Memory(":memory:")); a = Agent(e)
ITEMS = []
def check(i, desc, ok, info=""):
    ITEMS.append({"id": i, "desc": desc, "ok": bool(ok), "info": "" if ok else str(info)[:300]}); print(("PASS " if ok else "FAIL ") + i, desc, "" if ok else info)

r = e.sql_query("How many inspections were done by drone versus manual in 2025?")
got = {x["method"]: list(x.values())[1] for x in r["rows"]}; want = I[I.ts.dt.year == 2025].method.value_counts().to_dict()
check("Q1", "counts by method in 2025 match pandas", got == want, (got, want))
r = e.sql_query("Which technician had the highest total corrective repair cost in 2026, and how much?")
c = M[(M.maintenance_type == "corrective") & (M.ts.dt.year == 2026)].groupby("technician_user_id").cost.sum().sort_values(ascending=False)
check("Q2", "top technician by corrective cost matches pandas", r["rows"] and r["rows"][0][list(r["rows"][0])[0]] == users[c.index[0]] and abs(list(r["rows"][0].values())[1] - c.iloc[0]) < 1, (r["rows"][:1], users[c.index[0]], c.iloc[0]))
r = e.sql_query("What was the average wellhead temperature of WELL-0001 in August 2026?")
w = I[(I.asset_id == "WELL-0001") & (I.ts >= pd.Timestamp("2026-08-01", tz="UTC")) & (I.ts < pd.Timestamp("2026-09-01", tz="UTC"))].wellhead_temp_c.mean()
check("Q3", "average wellhead temp matches pandas", r["rows"] and abs(list(r["rows"][0].values())[0] - w) < 0.01, (r["rows"], w))
r = e.sql_query("List the 5 inspectors with the most manual inspections overall, with their counts.")
m = I[I.method == "manual"].inspector_user_id.value_counts().head(5)
check("Q4", "top-5 manual inspectors match pandas", [x[list(x)[1]] for x in r["rows"]] == list(m.values), (r["rows"][:5], list(m.values)))
for i, bad in enumerate(["DROP TABLE wells", "SELECT 1; SELECT 2", "SELECT * FROM read_csv('/etc/passwd')", "DELETE FROM inspections", "COPY wells TO '/tmp/x.csv'", "PRAGMA database_list", "INSERT INTO wells VALUES (1)"], 5):
    try: sqltool._validate(bad); ok = False
    except ValueError: ok = True
    check(f"Q{i}", f"validator rejects: {bad[:40]}", ok)
check("Q12", "validator accepts a plain SELECT and a WITH query", sqltool._validate("select 1") and sqltool._validate("WITH a AS (SELECT 1) SELECT * FROM a"))
o = a.ask("U-201", "s1", "Which inspector did the most drone inspections in 2026?")
check("Q13", "an open-ended question routes to sql_query", o["plan"].get("tool") == "sql_query" and o.get("sql"), o["plan"])
o = a.ask("U-201", "s2", "Which wells in Northeast Block 8 are not producing oil right now, and why?")
check("Q14", "a question a typed tool covers does NOT use sql_query", o["plan"].get("tool") == "wells_not_producing", o["plan"])
print("FAILS:", sum(not i["ok"] for i in ITEMS)); sys.path.insert(0, "tests"); import _results; _results.save("sql-tool", ITEMS)
