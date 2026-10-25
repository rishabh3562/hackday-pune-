"""Critic sub-agent: catches a planted contradiction / invented number / dropped row, and leaves a correct answer alone. Run: .venv/bin/python tests/critic_test.py"""
import json, os, sys
for l in open(".env"):
    k, v = l.strip().split("=", 1); os.environ.setdefault(k, v)
sys.path.insert(0, ".")
from copilot import critic
facts = json.dumps({"rows": [{"Well": "WELL-0108", "Type": "T350", "Corrective repairs (12 mo)": 3, "Threshold": 2}, {"Well": "WELL-0120", "Type": "T350", "Corrective repairs (12 mo)": 2, "Threshold": 2},
                              {"Well": "WELL-0121", "Type": "T200", "Corrective repairs (12 mo)": 3, "Threshold": 3}], "notes": ["Threshold for T350 wells is 2 repairs by Michael Turner's rule (manual says 3)."]})
Q = "Which wells in Northeast Block 7 need a root-cause analysis on their pump jack?"
ITEMS = []
def check(i, desc, ok, info=""):
    ITEMS.append({"id": i, "desc": desc, "ok": bool(ok), "info": str(info)[:300]}); print(("PASS " if ok else "FAIL ") + i, desc, "" if ok else info)
good = "WELL-0108, WELL-0120 and WELL-0121 need a root-cause analysis. WELL-0108 and WELL-0120 are T350 wells held to Michael Turner's rule of 2 repairs (the manual says 3); WELL-0121 is a T200 well with 3 repairs."
ok, p = critic.review(Q, facts, good); check("C1", "a correct draft is accepted", ok, p)
bad1 = "WELL-0108 and WELL-0121 need a root-cause analysis. WELL-0120 does not need one because it has only 2 repairs."
ok, p = critic.review(Q, facts, bad1); check("C2", "a draft that excludes a listed row is flagged", not ok and any("0120" in x for x in p), (ok, p))
bad2 = "WELL-0108, WELL-0120 and WELL-0121 need a root-cause analysis; WELL-0108 had 7 corrective repairs."
ok, p = critic.review(Q, facts, bad2); check("C3", "a draft with a wrong number is flagged", not ok, (ok, p))
bad3 = "WELL-0108, WELL-0120 and WELL-0121 need a root-cause analysis."
ok, p = critic.review(Q, facts, bad3); check("C4", "a draft that hides the user-rule/manual conflict is flagged", not ok, (ok, p))
print("FAILS:", sum(not i["ok"] for i in ITEMS)); sys.path.insert(0, "tests"); import _results; _results.save("critic", ITEMS)
