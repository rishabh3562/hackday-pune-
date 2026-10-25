"""Second tool group: fleet analytics (reliability, compliance, cost). Still deterministic, still no LLM."""
import pandas as pd

from .data import ANCHOR, TODAY
from .tools import Engine, WEEK_DAYS

END = TODAY + pd.Timedelta(days=1)


def _maint(self, area=None, well=None, wells=None, well_type=None, year=None, months=None, days=None, start=None, end=None,
           maintenance_type=None, equipment=None):
    ids = self.wells_in(well=well, wells=wells, area=area, well_type=well_type)
    a, b = self.period(days, months, None, year, start, end)
    m = self.ds.m
    m = m[m.asset_id.isin(ids) & (m.ts >= a) & (m.ts <= min(b, END))]
    if maintenance_type:
        m = m[m.maintenance_type == maintenance_type]
    if equipment:
        m = m[m.equipment_kind == equipment]
    return m


def repair_summary(self, group_by="well", area=None, well=None, well_type=None, year=None, months=None, days=None,
                   maintenance_type=None, equipment=None, min_count=None, top_n=None, metric="cost"):
    """Count/cost of repairs grouped by well | area | well_type | equipment | technician | contractor | month."""
    m = _maint(self, area=area, well=well, well_type=well_type, year=year, months=months, days=days,
               maintenance_type=maintenance_type, equipment=equipment).copy()
    key = {"well": "asset_id", "area": "area_id", "well_type": "well_type", "equipment": "equipment_kind",
           "technician": "technician_user_id", "contractor": "contractor"}.get(group_by)
    if group_by == "month":
        m["k"] = m.ts.dt.strftime("%Y-%m")
    else:
        m["k"] = m[key]
    g = m.groupby("k").agg(Repairs=("maintenance_id", "count"), Cost=("cost_total", "sum"), ids=("maintenance_id", list)).reset_index()
    if min_count:
        g = g[g.Repairs >= int(min_count)]
    g = g.sort_values(["Cost" if metric == "cost" else "Repairs", "k"], ascending=[False, True] if group_by != "month" else [False, True])
    if group_by == "month":
        g = g.sort_values("k")
    if top_n:
        g = g.head(int(top_n))
    label = {"well": "Well", "area": "Area", "well_type": "Type", "equipment": "Equipment", "technician": "Technician",
             "contractor": "Contractor", "month": "Month"}[group_by]
    rows = []
    for r in g.itertuples():
        k = r.k
        if group_by == "area":
            k = self.ds.area_name.get(k, k)
        if group_by == "technician":
            k = f"{self.uname(k)} ({k})"
        rows.append({label: k, "Repairs": int(r.Repairs), "Cost (USD)": int(r.Cost)})
    cites = [i for r in g.itertuples() for i in r.ids][:60]
    vis = "bar" if group_by in ("area", "well_type", "equipment", "technician", "contractor") else "table"
    if group_by == "month":
        vis = "line"
    return {"visual": vis, "rows": rows, "citations": cites, "notes": [f"Total {int(g.Cost.sum()):,} USD over {int(g.Repairs.sum())} repairs."]}


def top_repairs(self, n=5, year=None, months=None, days=None, area=None, maintenance_type=None):
    m = _maint(self, area=area, year=year, months=months, days=days, maintenance_type=maintenance_type)
    m = m.sort_values(["cost_total", "maintenance_id"], ascending=[False, True]).head(int(n))
    rows = [{"Repair": r.maintenance_id, "Well": r.asset_id, "Type": r.maintenance_type, "Equipment": r.equipment_kind,
             "Issue": r.issue, "Started": r.started_at[:10], "Cost (USD)": int(r.cost_total)} for r in m.itertuples()]
    return {"visual": "table", "rows": rows, "citations": list(m.maintenance_id), "notes": []}


def open_repairs_all(self, area=None):
    ids = self.wells_in(area=area)
    m = self.ds.m
    m = m[m.asset_id.isin(ids) & (m.ts <= TODAY) & (pd.to_datetime(m.completed_at, utc=True) > TODAY)]
    rows = [{"Well": r.asset_id, "Repair": r.maintenance_id, "Issue": r.issue, "Started": r.started_at[:10],
             "Planned end": r.completed_at[:10]} for r in m.itertuples()]
    return {"visual": "table", "rows": rows, "citations": list(m.maintenance_id), "notes": []}


def inspection_gaps(self, year=2026, min_days=14, area=None):
    """RC-01: wells with more than `min_days` between consecutive inspections."""
    ids = self.wells_in(area=area)
    a, b = self.period(year=year)
    i = self.ds.i[self.ds.i.asset_id.isin(ids) & (self.ds.i.ts >= a) & (self.ds.i.ts <= min(b, END))].sort_values("ts").copy()
    i["gap"] = i.groupby("asset_id").ts.diff().dt.days
    g = i[i.gap > float(min_days)]
    rows = [{"Well": r.asset_id, "Inspection": r.inspection_id, "Date": str(r.ts.date()), "Days since previous": int(r.gap)} for r in g.itertuples()]
    return {"visual": "table", "rows": rows, "citations": list(g.inspection_id), "notes": [f"RC-01 requires an inspection at least every {self.ds.rules['inspect_days']:g} days."]}


def fines(self, status="open", area=None):
    ids = self.wells_in(area=area)
    r = self.ds.r
    r = r[r.asset_id.isin(ids) & (r.fine_usd > 0)]
    if status in ("open", "closed"):
        r = r[r.status == status]
    rows = [{"Well": x.asset_id, "Event": x.event_id, "Date": x.date, "Fine (USD)": int(x.fine_usd), "Status": x.status, "Detail": x.detail} for x in r.itertuples()]
    return {"visual": "table", "rows": rows, "citations": list(r.event_id), "notes": [f"Total {int(r.fine_usd.sum()):,} USD ({status} fines)."]}


def downtime_trend(self, area=None, well=None, year=None, months=None, freq="month"):
    ids = self.wells_in(area=area, well=well)
    a, b = self.period(months=months, year=year)
    i = self.inspections()
    i = i[i.asset_id.isin(ids) & (i.ts >= a) & (i.ts <= min(b, END)) & ~i.producing].copy()
    i["k"] = i.ts.dt.strftime("%Y-%m") if freq == "month" else i.ts.dt.tz_localize(None).dt.to_period("Q").astype(str)
    g = i.groupby("k").size() * WEEK_DAYS
    rows = [{"Period": k, "Downtime (days)": int(v)} for k, v in g.items()]
    return {"visual": "line", "rows": rows, "citations": [], "notes": ["Sum over the selected wells; 7 days per non-producing weekly inspection."]}


def mtbf(self, group_by="well_type", area=None, months=None):
    """Mean days between consecutive corrective repairs (per well), averaged."""
    m = _maint(self, area=area, months=months, maintenance_type="corrective").sort_values("ts").copy()
    m["gap"] = m.groupby("asset_id").ts.diff().dt.days
    key = "well_type" if group_by == "well_type" else "asset_id"
    g = m.groupby(key).gap.mean().round(1)
    rows = [{("Type" if key == "well_type" else "Well"): k, "Mean days between corrective repairs": float(v)} for k, v in g.items() if pd.notna(v)]
    return {"visual": "bar", "rows": rows, "citations": [], "notes": ["Computed from gaps between consecutive corrective repair start dates on the same well."]}


def stale_status(self, area=None):
    ids = self.wells_in(area=area)
    L = self.latest(ids)
    rows = []
    for w, r in L.iterrows():
        rec = self.ds.w.loc[w, "recorded_status"]
        if (rec == "active") != bool(r.producing):
            rows.append({"Well": w, "Recorded status": rec, "Actually producing": bool(r.producing),
                         "Wellhead above air (°C)": round(float(r.delta), 1), "Last inspected": str(r.ts.date())})
    return {"visual": "table", "rows": rows, "citations": [x["Well"] for x in rows], "notes": ["Inspections are the truth; recorded status refreshes monthly."]}


def spill_breakdown(self, by="method", area=None, months=None, year=None, reportable_only=False, start_year=None):
    ids = self.wells_in(area=area)
    a, b = self.period(months=months, year=year)
    if start_year:
        a = pd.Timestamp(f"{int(start_year)}-01-01", tz="UTC")
    s = self._spill_df(ids, a, min(b, END)).copy()
    if reportable_only:
        s = s[s.spill_est_volume_bbl >= self.ds.rules["reportable_bbl"]]
    s["k"] = {"method": s.method, "area": s.area_id.map(self.ds.area_name)}.get(by) if by in ("method", "area") else s.ts.dt.tz_localize(None).dt.to_period("Q").astype(str)
    g = s.groupby("k").agg(Spills=("inspection_id", "count"), Barrels=("spill_est_volume_bbl", "sum"))
    rows = [{by.title(): k, "Spills": int(r.Spills), "Barrels": round(float(r.Barrels), 1)} for k, r in g.iterrows()]
    return {"visual": "line" if by == "quarter" else "bar", "rows": rows, "citations": list(s.inspection_id)[:60],
            "notes": ["Corrected detections excluded."]}


def consecutive_down(self, min_days=14, area=None):
    """RC-03: wells currently down for more than min_days of consecutive non-producing inspections."""
    ids = self.wells_in(area=area)
    i = self.inspections()
    i = i[i.asset_id.isin(ids) & (i.ts <= END)].sort_values("ts")
    rows, cites = [], []
    for w, df in i.groupby("asset_id"):
        n, last = 0, []
        for r in df.iloc[::-1].itertuples():
            if r.producing:
                break
            n += 1
            last.append(r.inspection_id)
        if n * WEEK_DAYS > float(min_days):
            rows.append({"Well": w, "Consecutive days down": n * WEEK_DAYS, "Since": str(df.iloc[-n].ts.date()),
                         "Recorded status": self.ds.w.loc[w, "recorded_status"]})
            cites += last
    return {"visual": "table", "rows": rows, "citations": cites,
            "notes": [f"RC-03: down more than {min_days} consecutive days must be reported to the area production supervisor."]}


def repeat_failures(self, days=90, year=2026, area=None):
    """Corrective repairs on the same well and equipment kind within `days` of the previous one."""
    m = _maint(self, area=area, year=year, maintenance_type="corrective").sort_values("ts").copy()
    m["gap"] = m.groupby(["asset_id", "equipment_kind"]).ts.diff().dt.days
    r = m[m.gap <= float(days)]
    g = r.groupby("asset_id").agg(Repeats=("maintenance_id", "count"), Equipment=("equipment_kind", lambda x: ", ".join(sorted(set(x)))),
                                  ids=("maintenance_id", list)).reset_index()
    rows = [{"Well": x.asset_id, "Repeat failures": int(x.Repeats), "Equipment": x.Equipment} for x in g.itertuples()]
    return {"visual": "table", "rows": rows, "citations": [i for x in g.ids for i in x][:60],
            "notes": [f"A repeat failure is a corrective repair on the same equipment within {days} days of the previous one."]}


def spill_response_summary(self, months=12, area=None):
    R = self.ds.rules
    ids = self.wells_in(area=area)
    a, b = self.period(months=months)
    s = self._spill_df(ids, a, END)
    s = s[s.spill_est_volume_bbl >= R["reportable_bbl"]]
    rows, late = [], 0
    reg = self.ds.r
    for r in s.sort_values("ts").itertuples():
        f = reg[(reg.related_inspection_id == r.inspection_id) & (reg.event_type == "spill_report_filed")]
        h = float(f.iloc[0].hours_to_report) if len(f) else None
        ok = h is not None and h <= self.ds.report_limit(r.ts)
        late += (not ok)
        rows.append({"Well": r.asset_id, "Date": str(r.ts.date()), "Barrels": r.spill_est_volume_bbl, "Inspection": r.inspection_id,
                     "Hours to report": h if h is not None else "no report on record", "On time": ok})
    fines_open = reg[(reg.asset_id.isin(ids)) & (reg.ts >= a) & (reg.status == "open")].fine_usd.sum()
    return {"visual": "table", "rows": rows, "citations": list(s.inspection_id), "late_or_missing": late,
            "notes": [f"{len(rows)} reportable spills, {late} late or unreported; open fines on events in the window: USD {int(fines_open):,}."]}


def spill_repair_cost(self, year=2026, area=None):
    ids = self.wells_in(area=area)
    a, b = self.period(year=year)
    spills = set(self.ds.i[self.ds.i.spill_detected].inspection_id)
    m = self.ds.m
    m = m[m.asset_id.isin(ids) & m.triggered_by_inspection_id.isin(spills) & (m.ts >= a) & (m.ts <= min(b, END))]
    g = m.groupby("area_id").agg(Repairs=("maintenance_id", "count"), Cost=("cost_total", "sum"))
    rows = [{"Area": self.ds.area_name[k], "Repairs": int(r.Repairs), "Cost (USD)": int(r.Cost)} for k, r in g.iterrows()]
    return {"visual": "bar", "rows": rows, "citations": list(m.maintenance_id)[:60], "notes": ["Repairs triggered by a spill detection, by start year."]}


def flowline_tests(self, year=2026, area=None):
    """RC-02: wells without an annual flowline integrity test in the given calendar year."""
    ids = self.wells_in(area=area)
    m = self.ds.m
    done = set(m[m.issue.str.contains("Annual flowline integrity test", na=False) & (m.ts.dt.year == int(year))].asset_id)
    miss = [w for w in ids if w not in done]
    by = {}
    for w in miss:
        by.setdefault(self.ds.area_name[self.ds.w.loc[w, "area_id"]], []).append(w)
    rows = [{"Area": a, "Wells without test": len(v), "Wells": ", ".join(v)} for a, v in sorted(by.items())]
    return {"visual": "bar", "rows": rows, "citations": [], "notes": [f"{len(miss)} of {len(ids)} wells have no annual flowline integrity test in {year} (RC-02)."]}


def hot_false_alarms(self, year=2025, min_temp=45):
    """Not-producing inspections where the wellhead still reads hot: absolute temperature is not production."""
    i = self.inspections()
    a, b = self.period(year=year)
    h = i[(i.ts >= a) & (i.ts <= b) & (i.wellhead_temp_c > float(min_temp)) & ~i.producing]
    g = h.groupby("area_id").size()
    rows = [{"Area": self.ds.area_name[k], "Hot but not producing": int(v)} for k, v in g.items()]
    return {"visual": "bar", "rows": rows, "citations": list(h.inspection_id)[:60],
            "notes": ["Only the rise over air temperature matters (manual section 9.3), never the absolute reading."]}


def down_with_recent_repair(self, days=90, area=None):
    ids = self.wells_in(area=area)
    L = self.latest(ids)
    L = L[~L.producing]
    m = self.ds.m
    m = m[m.asset_id.isin(L.index) & (m.maintenance_type == "corrective") & (m.ts >= ANCHOR - pd.Timedelta(days=int(days))) & (m.ts <= END)]
    rows = [{"Well": w, "Corrective repairs": int(len(g)), "Latest": g.sort_values("ts").iloc[-1].issue, "Repairs": ", ".join(g.maintenance_id)} for w, g in m.groupby("asset_id")]
    return {"visual": "table", "rows": rows, "citations": list(m.maintenance_id), "notes": ["Wells not producing now that had a corrective repair in the window."]}


def newly_stopped(self, area=None):
    ids = self.wells_in(area=area)
    i = self.inspections()
    i = i[i.asset_id.isin(ids) & (i.ts <= END)].sort_values("ts")
    rows, cites = [], []
    for w, df in i.groupby("asset_id"):
        if len(df) >= 2 and df.iloc[-2].producing and not df.iloc[-1].producing:
            r = df.iloc[-1]
            rows.append({"Well": w, "Stopped at inspection": r.inspection_id, "Date": str(r.ts.date()),
                         "Rise now (°C)": round(float(r.delta), 1), "Rise before (°C)": round(float(df.iloc[-2].delta), 1)})
            cites += [r.inspection_id, df.iloc[-2].inspection_id]
    return {"visual": "table", "rows": rows, "citations": cites, "notes": ["Producing at the previous inspection, not producing at the latest."]}


def correction_impact(self, year=2026):
    i = self.inspections()
    a, b = self.period(year=year)
    s = i[(i.ts >= a) & (i.ts <= min(b, END)) & i.orig_spill_detected]
    gone = s[~s.spill_detected]
    rows = [{"Inspection": r.inspection_id, "Well": r.asset_id, "Date": str(r.ts.date()), "Correction": r.correction} for r in gone.itertuples()]
    return {"visual": "table", "rows": rows, "citations": list(gone.inspection_id),
            "notes": [f"{len(s)} raw detections in {year}, {len(s) - len(gone)} real after corrections, {len(gone)} removed."]}


def downtime_cost(self, months=12, top_n=5):
    a, b = self.period(months=months)
    i = self.inspections()
    d = i[(i.ts >= a) & (i.ts <= END) & ~i.producing].groupby("asset_id").size().sort_values(ascending=False, kind="stable").head(int(top_n))
    m = self.ds.m
    rows = []
    for w, n in d.items():
        c = int(m[(m.asset_id == w) & (m.ts >= a) & (m.ts <= END)].cost_total.sum())
        rows.append({"Well": w, "Downtime (days)": int(n) * WEEK_DAYS, "Repair cost (USD)": c,
                     "Cost per downtime day (USD)": round(c / (int(n) * WEEK_DAYS))})
    return {"visual": "table", "rows": rows, "citations": [], "notes": ["Repair cost by start date within the same window."]}


for fn in (repair_summary, top_repairs, open_repairs_all, inspection_gaps, fines, downtime_trend, mtbf, stale_status, spill_breakdown,
           consecutive_down, repeat_failures, spill_response_summary, spill_repair_cost, flowline_tests, hot_false_alarms,
           down_with_recent_repair, newly_stopped, correction_impact, downtime_cost):
    setattr(Engine, fn.__name__, fn)
