"""Golden checks against 03-evaluation-queries (sample data). Run: .venv/bin/python tests/golden.py"""
import sys
sys.path.insert(0, ".")
from copilot.data import Dataset
from copilot.memory import Memory
from copilot.tools import Engine

root = sys.argv[1] if len(sys.argv) > 1 else "data/repo/sample-data"
e = Engine(Dataset(root), Memory(":memory:"))
fails = 0
ITEMS = []


def check(name, got, want):
    global fails
    ok = got == want
    fails += not ok
    ITEMS.append({"id": name, "desc": name, "ok": bool(ok)})
    print(("PASS " if ok else "FAIL ") + name, "" if ok else f"\n   got  {got}\n   want {want}")


s = e.well_status("WELL-0001")["rows"][0]
check("Q1", (s["producing"], s["inspection"], s["inspected_by"], s["recorded_status_stale"]), (False, "INS-0001-0203", "Ryan Brooks", True))
check("Q2", [r["Well"] for r in e.wells_not_producing("Northeast Block 8")["rows"]], ["WELL-0164", "WELL-0170", "WELL-0172", "WELL-0175"])
t = e.timeseries("WELL-0001", 13)
check("Q3", (len(t["rows"]), [r["date"] for r in t["rows"] if not r["producing"]]), (13, ["2026-10-08", "2026-10-15"]))
sp = e.spills(well="WELL-0001", months=48)
check("Q4", (sp["count"], sp["total_bbl"]), (6, 15.1))
check("Q5", e.downtime(well="WELL-0001", year=2025)["rows"][0]["Downtime (days)"], 21)
d = e.downtime(area="Northeast Block 7", months=4, top_n=3)["rows"]
check("Q6", {(r["Well"], r["Downtime (days)"]) for r in d}, {("WELL-0121", 49), ("WELL-0138", 42), ("WELL-0107", 42)})
sp = e.spills(area="Northeast Block 8", days=90)
check("Q7", sorted((r["Well"], r["Date"], r["Barrels"]) for r in sp["rows"]),
      [("WELL-0151", "2026-09-24", 4.5), ("WELL-0165", "2026-07-30", 1.2), ("WELL-0175", "2026-07-30", 3.9), ("WELL-0186", "2026-07-23", 0.6)])
h = e.spills(year=2026, group_by="area_month")["rows"]
check("Q8", {r["Area"]: r["Total"] for r in h}, {"Southwest Block 23": 35, "Southwest Block 24": 43, "Northeast Block 7": 37, "Northeast Block 8": 26})
c = e.compliance(well="WELL-0001", months=12)
check("Q9", sorted(r["Protocol"] for r in c["rows"]), ["RC-04", "SR-01", "SR-02", "SR-03"])
x = e.spills_over_containment("Southwest Block 24", 90)
check("Q10", sorted((r["Well"], r["Contained after (h)"]) for r in x["rows"]), [("WELL-0082", 7.1), ("WELL-0100", 8.1)])
rc = e.rca_candidates("Northeast Block 7", "pump_jack")
check("Q14a", [r["Well"] for r in rc["rows"]], ["WELL-0108", "WELL-0121", "WELL-0138"])
e.mem.add_fact(kind="rule", author="Michael Turner", scope_type="well_type", scope_id="T350", field="rca_count", corrected="2", text="rca after 2")
rc = e.rca_candidates("Northeast Block 7", "pump_jack")
check("Q14b", [r["Well"] for r in rc["rows"]], ["WELL-0108", "WELL-0120", "WELL-0121", "WELL-0138"])
rcost = e.repair_costs(["WELL-0121", "WELL-0138", "WELL-0107"], year=2026)
check("Q11", {r["Well"]: r["Total cost (USD)"] for r in rcost["rows"]}, {"WELL-0121": 25794, "WELL-0138": 46942, "WELL-0107": 5176})
# Q12: correction of raw data
e.mem.add_fact(kind="correction", author="Michael Turner", scope_type="well", scope_id="WELL-0164", inspection_id="INS-0164-0205",
               field="wellhead_temp_c", original="24.0", corrected="41.0", reason="faulty handheld thermal gun")
check("Q12", [r["Well"] for r in e.wells_not_producing("Northeast Block 8")["rows"]], ["WELL-0170", "WELL-0172", "WELL-0175"])
check("Q12b", e.well_status("WELL-0164")["rows"][0]["producing"], True)
# Q13: AI analysis correction
e.mem.add_fact(kind="correction", author="Michael Turner", scope_type="well", scope_id="WELL-0151", inspection_id="INS-0151-0201",
               field="spill_est_volume_bbl", original="4.5", corrected="5.4", reason="field crew measured")
c = e.compliance(well="WELL-0151", days=90)
check("Q13", {"SR-01", "SR-02", "SR-03"} <= {r["Protocol"] for r in c["rows"] + c["pending"]}, True)
q15 = e.spills(area="Northeast Block 8", days=90, reportable_only=True)
check("Q15", [r["Well"] for r in q15["rows"]], ["WELL-0151"])
# SQL system-of-record cross-check (raw producing flag, before corrections): WELL-0001 downtime 2025 = 21 days
from copilot.store import to_duckdb
import duckdb
con = duckdb.connect(to_duckdb(e.ds, "/tmp/golden_store.duckdb"), read_only=True)
n = con.execute("SELECT count(*)*7 FROM inspections_effective_raw WHERE asset_id='WELL-0001' AND year(ts)=2025 AND NOT producing").fetchone()[0]
check("SQL store Q5", n, 21)
print("FAILS:", fails)
sys.path.insert(0, "tests"); import _results; _results.save("golden", ITEMS)
