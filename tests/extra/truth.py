"""Independent ground truth for the 22 extra scenarios. Reads raw files directly (does NOT use copilot/)."""
import glob, json, sys
import pandas as pd

R = sys.argv[1] if len(sys.argv) > 1 else "data/repo/sample-data"
T = pd.Timestamp("2026-10-17", tz="UTC")
J = lambda f: [json.loads(l) for p in sorted(glob.glob(f"{R}/assets/*/{f}")) for l in open(p) if l.strip()]
W = pd.DataFrame([json.load(open(p)) for p in sorted(glob.glob(f"{R}/assets/*/metadata.json"))]).set_index("asset_id")
I = pd.DataFrame(J("inspections.jsonl")); I["ts"] = pd.to_datetime(I.inspected_at, utc=True)
M = pd.DataFrame(J("maintenance.jsonl")); M["ts"] = pd.to_datetime(M.started_at, utc=True); M["cost"] = M.cost_usd.map(lambda c: c["total"])
G = pd.DataFrame(J("regulatory-events.jsonl")); G["ts"] = pd.to_datetime(G.date, utc=True)
N = pd.DataFrame(J("context.jsonl"))
THR = {"T200": 15, "T350": 20}
AREA = {a["area_id"]: a["name"] for a in json.load(open(f"{R}/fleet/areas.json"))["areas"]}
for df in (I, M):
    df["type"] = df.asset_id.map(W.well_type); df["area"] = df.asset_id.map(W.area_id).map(AREA)
I["prod"] = (I.wellhead_temp_c - I.ambient_temp_c) >= I.type.map(THR)
corr = set(N[N.note_type == "correction"].inspection_id.dropna())
I["spill"] = I.spill_detected & ~I.inspection_id.isin(corr)
L = I[I.ts <= T + pd.Timedelta(days=1)].sort_values("ts").groupby("asset_id").tail(1).set_index("asset_id")
A = T - pd.Timedelta(days=1)  # windows anchor on the last day of data
y12 = A - pd.DateOffset(months=12)
out = {}

c = M[(M.maintenance_type == "corrective") & (M.ts >= y12) & (M.ts <= T)]
g = c[c.area == "Southwest Block 24"].groupby("asset_id").size()
out["M1"] = sorted(g[g >= 2].index)
out["M2"] = M[(M.ts.dt.year == 2025)].groupby("area").cost.sum().astype(int).to_dict()
gp = I[(I.ts.dt.year == 2026) & (I.ts <= T)].sort_values("ts")
gp["d"] = gp.groupby("asset_id").ts.diff().dt.days
out["M3"] = sorted(gp[gp.d > 14].asset_id.unique())  # RC-01: more than 14 days between inspections
op = G[(G.status == "open") & (G.fine_usd > 0)]
out["M4"] = {"total": int(op.fine_usd.sum()), "wells": sorted(op.asset_id.unique())}
d = I[(I.ts.dt.year == 2026) & (I.area == "Northeast Block 7") & ~I["prod"]]
out["M5"] = (d.groupby(d.ts.dt.month).size() * 7).to_dict()
cc = M[(M.maintenance_type == "corrective") & (M.ts <= T)].sort_values("ts")
cc["gap"] = cc.groupby("asset_id").ts.diff().dt.days
out["M6"] = {k: round(v, 1) for k, v in cc.groupby("type").gap.mean().items()}
m26 = M[(M.ts.dt.year == 2026) & (M.ts <= T)].sort_values("cost").iloc[-1]
out["M7"] = (m26.maintenance_id, int(m26.cost))
z = c[c.area == "Northeast Block 8"]
out["M8"] = z.technician_user_id.value_counts().head(3).to_dict()
Lm = L.join(W[["recorded_status"]])
st = Lm[(Lm.area == "Southwest Block 23") & ((Lm.recorded_status == "active") != Lm["prod"])]
out["M9"] = sorted(st.index)
sp = I[I.spill & (I.ts >= y12) & (I.ts <= T + pd.Timedelta(days=1))]
out["M10"] = sp.method.value_counts().to_dict()
op_r = M[(pd.to_datetime(M.completed_at, utc=True) > T) & (M.ts <= T)]
out["M11"] = sorted(op_r.asset_id.unique())

def trailing(df):  # consecutive non-producing at the end
    n = 0
    for p in df.sort_values("ts")["prod"][::-1]:
        if p: break
        n += 1
    return n
tr = {w: trailing(df[df.ts <= T + pd.Timedelta(days=1)]) for w, df in I.groupby("asset_id")}
out["C1"] = sorted(w for w, n in tr.items() if n * 7 > 14)
rep = []
for (w, e), df in M[(M.maintenance_type == "corrective") & (M.ts.dt.year == 2026)].sort_values("ts").groupby(["asset_id", "equipment_kind"]):
    if (df.ts.diff().dt.days <= 90).any(): rep.append(w)
out["C2"] = sorted(set(rep))
rp = I[I.spill & (I.spill_est_volume_bbl >= 5) & (I.ts >= y12)]
late = []
for r in rp.itertuples():
    f = G[(G.related_inspection_id == r.inspection_id) & (G.event_type == "spill_report_filed")]
    if len(f) and f.iloc[0].hours_to_report > 24 or not len(f): late.append(r.inspection_id)
out["C3"] = {"reportable": len(rp), "late_or_missing": len(late), "fines_open": int(G[(G.ts >= y12) & (G.status == "open")].fine_usd.sum())}
trig = M[M.triggered_by_inspection_id.isin(I[I.spill].inspection_id) & (M.ts.dt.year == 2026) & (M.ts <= T)]
out["C4"] = trig.groupby("area").cost.sum().astype(int).to_dict()
ft = M[M.issue.str.contains("Annual flowline integrity test", na=False) & (M.ts.dt.year == 2026)].asset_id.unique()
miss = W[~W.index.isin(ft)]
out["C5"] = {AREA[a]: int(n) for a, n in miss.area_id.value_counts().items()}
hot = I[(I.ts.dt.year == 2025) & (I.wellhead_temp_c > 45) & ~I["prod"]]
out["C6"] = hot.groupby("area").size().to_dict()
rs = M[(M.maintenance_type == "corrective") & (M.ts >= A - pd.Timedelta(days=90)) & (M.ts <= T)].asset_id.unique()
nn = L[~L["prod"]]
out["C7"] = sorted(set(nn.index) & set(rs))  # not producing now AND corrective repair in last 90 days
prev = I[I.ts <= T + pd.Timedelta(days=1)].sort_values("ts").groupby("asset_id").nth(-2).set_index("asset_id")
out["C8"] = sorted(w for w in L.index if w in prev.index and prev.loc[w, "prod"] and not L.loc[w, "prod"])
s26 = I[(I.ts.dt.year == 2026) & I.spill_detected]
out["C9"] = {"detected": int(len(s26)), "real": int(s26.spill.sum()), "corrected_out": int((~s26.spill).sum())}
dt = I[(I.ts >= y12) & ~I["prod"]].groupby("asset_id").size() * 7
top = dt.sort_values(ascending=False, kind="stable").head(5)
out["C10"] = {w: (int(v), int(M[(M.asset_id == w) & (M.ts >= y12) & (M.ts <= T)].cost.sum())) for w, v in top.items()}
q = I[I.spill & (I.spill_est_volume_bbl >= 5) & (I.ts.dt.year >= 2023) & (I.ts <= T + pd.Timedelta(days=1))]
out["C11"] = q.groupby(q.ts.dt.tz_localize(None).dt.to_period("Q").astype(str)).size().to_dict()

if __name__ == "__main__":
    for k, v in out.items(): print(k, v)
