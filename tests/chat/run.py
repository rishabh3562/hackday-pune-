"""Third suite (S1..S24): scenarios from the mentor / friend discussion. Stateful, so memory is reset per group.
Expected values come from independent pandas code on the raw files. Run: .venv/bin/python -u tests/chat/run.py [ids | core]"""
import glob, json, os, sys, time
sys.path.insert(0, ".")
os.environ["TRACE_FILE"] = "/dev/null"
for l in open(".env"):
    k, v = l.strip().split("=", 1); os.environ.setdefault(k, v)
import pandas as pd
from copilot.data import Dataset
from copilot.memory import Memory
from copilot.tools import Engine
from copilot.agent import Agent
R = "data/repo/sample-data"
CORE = {"S1", "S2", "S5", "S7", "S10", "S12", "S15", "S18", "S26", "S28"}   # the 10 core scenarios (18 given + 22 extra + 10 = 50)
only = (CORE if sys.argv[1:2] == ["core"] else set(sys.argv[1].split(","))) if len(sys.argv) > 1 else None
T = pd.Timestamp("2026-10-17", tz="UTC")
J = lambda f: [json.loads(l) for p in sorted(glob.glob(f"{R}/assets/*/{f}")) for l in open(p) if l.strip()]
W = pd.DataFrame([json.load(open(p)) for p in sorted(glob.glob(f"{R}/assets/*/metadata.json"))]).set_index("asset_id")
I = pd.DataFrame(J("inspections.jsonl")); I["ts"] = pd.to_datetime(I.inspected_at, utc=True)
M = pd.DataFrame(J("maintenance.jsonl")); M["ts"] = pd.to_datetime(M.started_at, utc=True)
AREA = {a["area_id"]: a["name"] for a in json.load(open(f"{R}/fleet/areas.json"))["areas"]}
THR = {"T200": 15, "T350": 20}
for d in (I, M):
    d["type"] = d.asset_id.map(W.well_type); d["area"] = d.asset_id.map(W.area_id).map(AREA)
ds = Dataset(R)

def fresh(mode="auto"):
    a = Agent(Engine(ds, Memory(":memory:"))); a.mode = mode
    return a
CUR = []
def ask(a, u, c, q):
    o = a.ask(u, c, q); CUR.append({"user": a.e.uname(u), "q": q, "a": o["text"], "tool": o["plan"].get("tool") or o["plan"].get("kind")}); return o
def not_producing(area, shift=None, sel=None):
    """truth: wells in area whose latest inspection is not producing, after an optional +shift on rows matching sel(df)."""
    L = I[(I.area == area) & (I.ts <= T + pd.Timedelta(days=1))].sort_values("ts").copy()
    if shift is not None:
        m = sel(L); L.loc[m, "wellhead_temp_c"] = L.loc[m, "wellhead_temp_c"] + shift
    L = L.groupby("asset_id").tail(1)
    return sorted(L[(L.wellhead_temp_c - L.ambient_temp_c) < L.type.map(THR)].asset_id)
def names(o):
    return sorted(r["Well"] for r in o.get("rows", []))
MT, JR, TH, JM = "U-201", "U-202", "U-204", "U-102"
RES = []
ITEMS = []
def run(sid, desc, fn):
    if only and sid not in only:
        return
    t = time.time(); CUR.clear()
    try:
        ok, info = fn()
    except Exception as ex:  # noqa: BLE001
        ok, info = False, f"EXC {ex!r}"
    ok = bool(ok); RES.append(ok); ITEMS.append({"id": sid, "desc": desc, "ok": ok, "core": sid in CORE, "ms": int((time.time() - t) * 1000), "info": str(info)[:300], "answers": list(CUR)})
    print(("PASS " if ok else "FAIL ") + sid, desc, ("" if ok else f"\n     {info}"), flush=True)

# ---------- feedback applies to many rows ----------
SEP = lambda L: (L.method == "manual") & (L.ts >= pd.Timestamp("2026-09-01", tz="UTC")) & (L.ts <= pd.Timestamp("2026-10-15 23:59", tz="UTC"))
def s1():
    a = fresh(); base = names(ask(a, MT, "c1", "Which wells in Northeast Block 8 are not producing oil right now, and why?"))
    o = ask(a, MT, "c1", "All manual-method readings in Northeast Block 8 between 1 Sep and 15 Oct 2026 were taken with a gun that reads 6 degrees too low; add 6 degrees to them.")
    after = names(ask(a, MT, "c1", "Which wells in Northeast Block 8 are not producing oil right now, and why?"))
    want = not_producing("Northeast Block 8", 6, SEP)
    n = int(((I.area == "Northeast Block 8") & SEP(I)).sum())
    return (after == want and base == not_producing("Northeast Block 8") and f"{n} inspections" in o["text"].replace("  ", " ") or str(n) in o["text"]) and after == want, (base, after, want, n, o["text"][:160])
run("S1", "multi-row 'add' correction applies to every matched row and changes the area answer", s1)
def s2():
    a = fresh(); orig = names(ask(a, MT, "c1", "Which wells in Northeast Block 8 are not producing oil right now?"))
    ask(a, MT, "c1", "All manual-method readings in Northeast Block 8 between 1 Sep and 15 Oct 2026 read 6 degrees too low; add 6 degrees.")
    ask(a, MT, "c1", "Undo my last correction.")
    back = names(ask(a, MT, "c1", "Which wells in Northeast Block 8 are not producing oil right now?"))
    st = [f["status"] for f in a.e.mem.facts(include_inactive=True) if f["kind"] == "correction"]
    return back == orig and st == ["revoked"], (orig, back, st)
run("S2", "'undo' revokes: originals restored, record kept as revoked in the audit log", s2)
def s3():
    a = fresh()
    q = "All manual-method readings for WELL-0164 and WELL-0172 between 1 Sep and 15 Oct 2026 read %s degrees too low; add %s degrees."
    ask(a, MT, "c1", q % (3, 3)); ask(a, MT, "c1", q % (5, 5))
    f = a.e.mem.facts(include_inactive=True)
    i = a.e.inspections(); r = i[i.inspection_id == "INS-0164-0205"].iloc[0]
    return len(f) == 2 and [x["status"] for x in f] == ["superseded", "confirmed"] and abs(r.wellhead_temp_c - (r.orig_wellhead_temp_c + 5)) < 1e-6, ([x["status"] for x in f], r.wellhead_temp_c, r.orig_wellhead_temp_c)
run("S3", "a newer correction on the same selector supersedes the older one (+5 applies, not +8)", s3)
def s4():
    a = fresh()
    ask(a, MT, "c1", "All readings in Northeast Block 8 between 1 Oct and 15 Oct 2026 read 2 degrees too low; add 2 degrees.")
    ask(a, MT, "c1", "For WELL-0164 only, the 15 Oct reading is 41.0 degrees, the field crew re-measured it.")
    i = a.e.inspections(); r = i[i.inspection_id == "INS-0164-0205"].iloc[0]
    return abs(r.wellhead_temp_c - 41.0) < 1e-6 and r.well_type == "T200", (r.wellhead_temp_c,)
run("S4", "most specific scope wins: well/inspection-level value beats the area-wide shift", s4)
def s5():
    a = fresh(); ask(a, MT, "c1", "New rule: all T200 wells need a root-cause analysis after 4 corrective repairs, not 3.")
    o = ask(a, MT, "c2", "Which wells in Northeast Block 7 need a root-cause analysis on their pump jack?")
    c = M[(M.maintenance_type == "corrective") & (M.equipment_kind == "pump_jack") & (M.area == "Northeast Block 7") & (M.ts >= pd.Timestamp("2025-10-16", tz="UTC")) & (M.ts <= T)]
    cnt = c.groupby("asset_id").size(); want = sorted(w for w, n in cnt.items() if n >= (4 if W.loc[w, "well_type"] == "T200" else 3))
    return names(o) == want, (names(o), want)
run("S5", "a well-type rule changes only that type's threshold (T200: 4, T350 stays 3), applied in a new chat", s5)
def s6():
    a = fresh(); o = ask(a, MT, "c1", "All the readings in the whole field are wrong, fix them.")
    i = a.e.inspections()
    return (not a.e.mem.facts(kind="correction")) and (i.orig_wellhead_temp_c == i.wellhead_temp_c).all(), (o["text"][:200], a.e.mem.facts())
run("S6", "a vague, unscoped feedback never silently rewrites the fleet (nothing is recorded; it asks)", s6)

# ---------- recall over time, ambiguity, privacy ----------
def s7():
    a = fresh(); ask(a, MT, "c1", "Which 3 wells in Northeast Block 7 had the most downtime in the last 4 months? Show a bar chart.")
    a.e.mem.db.execute("UPDATE convo SET ts='2026-04-10T09:00:00Z'"); a.e.mem.db.commit()
    o = ask(a, MT, "c9", "For the three wells we discussed in April, what have repairs cost this year?")
    return names(o) == ["WELL-0107", "WELL-0121", "WELL-0138"] and "No conversation" not in " ".join(o.get("notes", [])), (names(o), o.get("notes"))
run("S7", "'the wells we discussed in April' resolves a 6-month-old conversation by its timestamp", s7)
def s8():
    a = fresh(); ask(a, MT, "c1", "Which 3 wells in Northeast Block 7 had the most downtime in the last 4 months?")
    a.e.mem.db.execute("UPDATE convo SET ts='2026-04-10T09:00:00Z'"); a.e.mem.db.commit()
    o = ask(a, MT, "c9", "For the three wells we discussed yesterday, what have repairs cost this year?")
    return "No conversation" in " ".join(o.get("notes", [])) and names(o) == ["WELL-0107", "WELL-0121", "WELL-0138"], (names(o), o.get("notes"))
run("S8", "'yesterday' with nothing yesterday: falls back to the latest match and says so", s8)
def s9():
    a = fresh(); ask(a, MT, "c1", "Which 3 wells in Northeast Block 7 had the most downtime in the last 4 months?")
    ask(a, MT, "c1", "Which 3 wells in Northeast Block 8 had the most downtime in the last 4 months?")
    o = ask(a, MT, "c2", "For the three wells we discussed, what have repairs cost this year?")
    return any("Other sets" in n for n in o.get("notes", [])) and len(o["rows"]) == 3, (o.get("notes"),)
run("S9", "two different 3-well sets in history: uses the latest and lists the other set for the user to confirm", s9)
def s10():
    a = fresh(); ask(a, MT, "c1", "Which 3 wells in Northeast Block 7 had the most downtime in the last 4 months?")
    o = ask(a, JR, "j1", "For the three wells we discussed yesterday, what have repairs cost this year?")
    o2 = ask(a, MT, "c2", "For the three wells we discussed, what have repairs cost this year?")
    return not o["rows"] and len(o2["rows"]) == 3, (o["text"][:100], len(o2["rows"]))
run("S10", "private memory: another user is refused, the owner is unaffected by that attempt", s10)
def s11():
    a = fresh(); ask(a, JM, "m1", "FYI for everyone: WELL-0007 will be shut in from 17 Oct for a 10-day planned workover.")
    o = ask(a, TH, "t1", "Is any downtime planned for WELL-0007?")
    return "Jake" in o["text"] or "Morales" in o["text"], (o["text"][:200],)
run("S11", "shared knowledge from one user is visible to a different user, attributed to its author", s11)
def s12():
    a = fresh(); ask(a, MT, "c1", "Which wells in Northeast Block 8 are not producing oil right now?")
    o = ask(a, MT, "c1", "Show that as a bar chart instead.")
    return o["plan"].get("kind") == "rerender" and o["visual"] == "bar" and len(o["rows"]) == 4, (o["plan"], o.get("visual"), len(o.get("rows", [])))
run("S12", "'show it as a bar chart' re-renders the previous result without re-querying", s12)
def s13():
    a = fresh(); o = ask(a, MT, "c1", "Is WELL-0001 producing right now, and how many spills has it had in the last 4 years?")
    return len(o.get("parts", [])) == 2, (o["plan"],)
run("S13", "a two-part question returns two result blocks (compound plan)", s13)
def s14():
    a = fresh(); ask(a, MT, "c1", "Is WELL-0175 producing oil right now?")
    ask(a, MT, "c1", "WELL-0175 has been shut in for planned work since 14 Oct.")
    f = a.e.mem.facts(kind="note")
    return f and f[-1]["status"] == "confirmed", ([x["status"] for x in f],)
run("S14", "a claim that agrees with the latest inspection is stored as confirmed", s14)

# ---------- concepts, links, documents ----------
def s15():
    a = fresh(); o = ask(a, MT, "c1", "Which wells are failing due to mud?")
    # the property: it must SAY the word is absent from the records (never silently list sand wells under "mud")
    return any(("No record mentions" in n) or ("literally" in n) or ("No root cause" in n) for n in o.get("notes", [])), (o["plan"], o.get("notes"))
run("S15", "'mud' appears in no record: no invented matches, says so, offers the nearest causes", s15)
def s16():
    a = fresh(); o = ask(a, MT, "c1", "Which wells in Northeast Block 7 had corrosion as the root cause of repairs in the last 12 months?")
    import re
    rows = []
    for m in M[(M.area == "Northeast Block 7") & (M.ts >= pd.Timestamp("2025-10-16", tz="UTC")) & (M.ts <= T)].itertuples():
        t = ds.reports.get(m.maintenance_id)
        rc = re.search(r"## Root cause\s*\n+(.+?)(?:\n\s*\n|\n## |\Z)", t or "", re.S)
        if rc and "corros" in rc.group(1).split(".")[0].lower():
            rows.append(m.asset_id)
    want = sorted(set(rows)); got = names(o)
    return set(got) <= set(want) and len(got) >= 0.8 * len(want) and "corros" in json.dumps(o["rows"]).lower(), (len(got), len(want), sorted(set(want) - set(got))[:5])
run("S16", "concept search: corrosion wells in an area match the independent regex ground truth (>=80% recall, no false wells)", s16)
def s17():
    a = fresh(); o = ask(a, MT, "c1", "Which wells had sand-related failures in the last 12 months?")
    return bool(o["rows"]) and all(("sand" in r["Root cause (quote)"].lower() or "scale" in r["Root cause (quote)"].lower()) for r in o["rows"]), (len(o["rows"]), o.get("notes", [])[:2])
run("S17", "synonym/related concept (sand) returns wells whose quoted root cause really says sand/scale", s17)
def s18():
    a = fresh(); o = ask(a, MT, "c1", "What is connected to inspection INS-0001-0185?")
    ids = {r["ID"] for r in o["rows"]}
    return {"MNT-0001-029", "REG-0001-001", "REG-0001-002", "REG-0001-003"} <= ids, (ids,)
run("S18", "entity trace walks the ID links: inspection -> repair -> regulator events (no graph DB)", s18)
def s19():
    e = fresh().e
    top = lambda q, k=5: [r["doc"] for r in e.search_docs(q, k)["rows"]]
    a1 = any("T350" in d for d in top("what does the T350 manual say about producing temperature", 3))
    a2 = any("spill-response" in d for d in top("SR-02 containment time limit", 3))
    a3 = any("spill-response" in d for d in top("how quickly must a leak be contained after it is found", 5))
    return a1 and a2 and a3, (a1, a2, a3)
run("S19", "hybrid search: manual by name, exact protocol ID, and a paraphrase all find the right document", s19)
def s20():
    a = fresh(); o1 = ask(a, MT, "c1", "What temperature rise above air means WELL-0007 is producing, and where does that rule come from?")
    o2 = ask(a, MT, "c1", "What temperature rise above air means WELL-0001 is producing, and where does that rule come from?")
    t1, t2 = o1["text"], o2["text"]
    return "20" in t1 and "T350" in t1 and "15" in t2 and "T200" in t2, (t1[:160], t2[:160])
run("S20", "SOP/manual applicability per well: WELL-0007 (T350) gets 20 °C, WELL-0001 (T200) gets 15 °C, with the source", s20)

# ---------- robustness ----------
def s21():
    sys.path.insert(0, "tests")
    if not os.path.exists("data/fake_test/sample-data"):
        os.system(".venv/bin/python tests/make_fake_testroot.py >/dev/null")
    d2 = Dataset(R, "data/fake_test"); d3 = Dataset(R, "data/fake_test", R)
    e = Engine(d2, Memory(":memory:"))
    e.wells_not_producing("Northwest Block 31")
    return len(d2.w) == 205 and len(d3.w) == 205 and len(d3.i) == len(d2.i) and len(d2.areas) == 5 and e.well_status("WELL-0201")["rows"], (len(d2.w), len(d3.i), len(d2.i), len(d2.areas))
run("S21", "loading a second dataset root (new wells + area) works; loading a root twice is idempotent", s21)
def s22():
    a = fresh(); o = ask(a, MT, "c1", "Is WELL-9999 producing right now?")
    return "No inspections" in o["text"] or "not" in o["text"].lower() or "could not" in o["text"].lower(), (o["text"][:200],)
run("S22", "unknown well: graceful answer, no crash", s22)
def s23():
    a = fresh(); r1 = names(ask(a, MT, "c1", "Which wells in NE-8 are not producing oil right now?")); r2 = names(ask(a, MT, "c1", "Which wells in northeast block 8 are not producing oil right now?"))
    return r1 == r2 == not_producing("Northeast Block 8"), (r1, r2)
run("S23", "area aliases (NE-8, lower case) resolve to the same area", s23)
def s24():
    a = fresh(); ask(a, MT, "c1", "The 15 Oct reading for WELL-0164 is wrong; the crew re-measured it at 41.0 °C.")
    pj = ask(a, JR, "j1", "Is WELL-0164 producing oil right now?")
    f = a.e.mem.facts(kind="correction")
    return f and "41" in pj["text"] and "Michael" in pj["text"], (pj["text"][:200],)
run("S24", "a correction by one user is used, and attributed, in another user's later answer", s24)
# ---------- clarification loop ----------
def s25():
    a = fresh("ask"); ask(a, MT, "c1", "Which 3 wells in Northeast Block 7 had the most downtime in the last 4 months?")
    ask(a, MT, "c1", "Which 3 wells in Northeast Block 8 had the most downtime in the last 4 months?")
    o = ask(a, MT, "c2", "For the three wells we discussed, what have repairs cost this year?")
    o2 = ask(a, MT, "c2", o["options"][-1]) if o.get("options") else {}
    return o.get("visual") == "clarify" and len(o["options"]) == 2 and len(o2.get("rows", [])) == 3, (o.get("visual"), o.get("options"), len(o2.get("rows", [])))
run("S25", "recall ambiguity in ask mode: asks which set (options), then answers with the chosen one", s25)
def s26():
    a = fresh("ask"); o = ask(a, MT, "c1", "Show me downtime.")
    ok1 = o.get("visual") == "clarify" and 2 <= len(o.get("options", [])) <= 4
    o2 = ask(a, MT, "c1", "Northeast Block 7, last 4 months, top 3")
    return ok1 and bool(o2.get("rows")) and o2["plan"].get("tool") == "downtime", (o.get("visual"), o.get("options"), o2["plan"])
run("S26", "ambiguous request: one short question with 2-4 options, the free-text reply completes the original request", s26)
def s27():
    a = fresh("auto"); o = ask(a, MT, "c1", "Show me downtime.")
    return o.get("visual") != "clarify" and bool(o.get("rows")) and any("Assumed" in n for n in o.get("notes", [])), (o.get("visual"), o.get("notes"))
run("S27", "auto mode (no human to answer): never asks, answers with the assumption stated", s27)
def s28():
    q = "Add 1 degree to every wellhead reading of every well in 2026, the fleet gun was miscalibrated."
    a = fresh("ask"); o = ask(a, MT, "c1", q)
    asked = o.get("visual") == "clarify" and not a.e.mem.facts(kind="correction")
    ask(a, MT, "c1", "Apply to all")
    done = len(a.e.mem.facts(kind="correction")) == 1
    b = fresh("ask"); ask(b, MT, "c1", q); ask(b, MT, "c1", "No")
    return asked and done and not b.e.mem.facts(kind="correction"), (o.get("visual"), asked, done, len(b.e.mem.facts(kind="correction")))
run("S28", "a change touching thousands of rows asks first; 'Apply' applies, 'No' records nothing", s28)
def s29():
    a = fresh("ask"); o = ask(a, MT, "c1", "Which wells in Northeast Block 9 are not producing oil right now?")
    return o.get("visual") == "clarify" and any("Northeast Block 8" in x for x in o.get("options", [])), (o.get("visual"), o.get("options"), o["text"][:100])
run("S29", "unknown area: asks and offers the real areas as options", s29)
print(f"passed {sum(RES)} of {len(RES)}")
if not only:
    sys.path.insert(0, "tests"); import _results; _results.save("design-review", ITEMS)
