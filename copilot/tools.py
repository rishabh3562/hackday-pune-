"""Deterministic analytics tools. No LLM in here. Every result: {rows, citations, notes, visual}."""
import json

import pandas as pd
from pandas.tseries.offsets import DateOffset

from .data import ANCHOR, TODAY, Dataset
from .memory import Memory

WEEK_DAYS = 7


class Engine:
    def __init__(self, ds: Dataset, mem: Memory):
        self.ds, self.mem = ds, mem
        self.overlay_conflicts = []

    # ---------- periods ----------
    def period(self, days=None, months=None, weeks=None, year=None, start=None, end=None):
        if year:
            return pd.Timestamp(f"{int(year)}-01-01", tz="UTC"), pd.Timestamp(f"{int(year)}-12-31 23:59:59", tz="UTC")
        e = pd.Timestamp(end, tz="UTC") if end else TODAY + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        if start:
            return pd.Timestamp(start, tz="UTC"), e
        if days:
            return (ANCHOR - pd.Timedelta(days=int(days))).normalize(), e
        if weeks:
            return (ANCHOR - pd.Timedelta(weeks=int(weeks))).normalize(), e
        if months:
            return (ANCHOR - DateOffset(months=int(months))).normalize(), e
        return pd.Timestamp("1900-01-01", tz="UTC"), e

    # ---------- scope ----------
    def wells_in(self, well=None, wells=None, area=None, well_type=None):
        w = self.ds.w
        if well:
            w = w[w.asset_id == well]
        if wells:
            w = w[w.asset_id.isin(wells)]
        if area:
            a = self.resolve_area(area)
            w = w[w.area_id == a]
        if well_type:
            w = w[w.well_type == well_type]
        return list(w.asset_id)

    def resolve_area(self, q):
        q = str(q).lower().strip()
        for a in self.ds.areas:
            if q in (a["area_id"].lower(), a["name"].lower()) or a["name"].lower() in q or a["area_id"].lower() == q:
                return a["area_id"]
        for a in self.ds.areas:
            if a["area_id"].lower().replace("-", " ") in q.replace("-", " "):
                return a["area_id"]
        raise ValueError(f"Unknown area '{q}'")

    # ---------- effective (corrected) inspections ----------
    def _specificity(self, f):
        sel = json.loads(f["selector"]) if f.get("selector") else {}
        if f.get("inspection_id") or sel.get("inspection_ids"):
            return 4
        if sel.get("wells") or f.get("scope_type") == "well":
            return 3
        return 2 if sel.get("area") else 1

    def _selector_mask(self, i, f):
        """Boolean row mask for a correction: legacy single-inspection facts or a JSON selector."""
        if f.get("inspection_id"):
            return i.inspection_id == f["inspection_id"]
        sel = json.loads(f["selector"]) if f.get("selector") else {}
        m = pd.Series(True, index=i.index)
        if sel.get("inspection_ids"):
            m &= i.inspection_id.isin(sel["inspection_ids"])
        if sel.get("wells"):
            m &= i.asset_id.isin(sel["wells"])
        if sel.get("well_type"):
            m &= i.well_type == sel["well_type"]
        if sel.get("area"):
            m &= i.area_id == sel["area"]
        if sel.get("date_from"):
            m &= i.ts >= pd.Timestamp(sel["date_from"], tz="UTC")
        if sel.get("date_to"):
            m &= i.ts <= pd.Timestamp(sel["date_to"], tz="UTC") + pd.Timedelta(days=1)
        for k, v in (sel.get("where") or {}).items():
            if k in i.columns:
                m &= i[k] == v
        if not (sel.get("inspection_ids") or sel.get("wells") or sel.get("well_type") or sel.get("area") or sel.get("date_from")):
            return pd.Series(False, index=i.index)   # an empty selector must never match the whole fleet by accident
        return m

    def inspections(self):
        """Raw inspections with corrections applied as an overlay; originals are kept in orig_* columns."""
        # the overlay only changes when the corrections log changes, so cache it on that signature
        sig = tuple((f["id"], f["status"]) for f in self.mem.facts(kind="correction", include_inactive=True))
        hit = getattr(self, "_inspections_cache", None)
        if hit and hit[0] == sig:
            self.overlay_conflicts = hit[2]
            return hit[1]
        self.overlay_conflicts = []
        i = self.ds.i.copy()
        i["orig_wellhead_temp_c"] = i["wellhead_temp_c"]
        i["orig_spill_volume"] = i["spill_est_volume_bbl"]
        i["orig_spill_detected"] = i["spill_detected"]
        i["correction"] = None
        # seed correction notes: override the detection
        for _, n in self.ds.n[self.ds.n.note_type == "correction"].iterrows():
            iid = n.get("inspection_id")
            if isinstance(iid, str):
                mask = i.inspection_id == iid
                i.loc[mask, "spill_detected"] = False
                i.loc[mask, "correction"] = f"{n['note_id']}: {n['text']}"
        # data_correction notes shipped with the data: the corrected value replaces the recorded one (originals stay in orig_*)
        for _, n in self.ds.n[self.ds.n.note_type == "data_correction"].iterrows():
            col = n.get("field")
            if col in i.columns and isinstance(n.get("inspection_id"), str):
                mask = i.inspection_id == n["inspection_id"]
                i.loc[mask, col] = n["corrected_value"]
                i.loc[mask, "correction"] = f"{n['note_id']}: {n['text']}"
        # runtime corrections: a selector (well/well list/type/area + dates + inspection ids) can match many rows; applied least
        # specific first so the most specific, latest correction wins; overlapping different values are reported as conflicts
        touched = {}
        facts = sorted(self.mem.facts(kind="correction"), key=lambda f: (self._specificity(f), f["id"]))
        for f in facts:
            mask = self._selector_mask(i, f)
            if not mask.any():
                continue
            _op = f.get("op") or "set"
            tag = (f"{f['author']}: {f['field']} {f['original'] or ''} -> {f['corrected']} ({f['reason']})" if _op == "set" else
                   f"{f['author']}: {f['field']} {'shifted by' if _op == 'add' else 'scaled by'} {f['corrected']} ({f['reason']})")
            col = {"wellhead_temp_c": "wellhead_temp_c", "spill_est_volume_bbl": "spill_est_volume_bbl",
                   "ambient_temp_c": "ambient_temp_c", "spill_detected": "spill_detected"}.get(f["field"])
            if not col:
                continue
            op = f.get("op") or "set"
            if col == "spill_detected":
                i.loc[mask, col] = str(f["corrected"]).lower() in ("true", "1", "yes")
            elif op == "add":
                i.loc[mask, col] = i.loc[mask, col] + float(f["corrected"])
            elif op == "mul":
                i.loc[mask, col] = i.loc[mask, col] * float(f["corrected"])
            else:
                i.loc[mask, col] = float(f["corrected"])
            for iid in i.loc[mask, "inspection_id"]:
                prev = touched.get((iid, col))
                if prev and prev[1] != (op, f["corrected"]):
                    self.overlay_conflicts.append({"inspection": iid, "field": col, "kept": f"#{f['id']} {f['author']}", "overridden": f"#{prev[0]}"})
                touched[(iid, col)] = (f["id"], (op, f["corrected"]))
            i.loc[mask, "correction"] = tag
        i["delta"] = i["wellhead_temp_c"] - i["ambient_temp_c"]
        thr = i["well_type"].map(self.ds.rules["producing_delta"])
        for w, hist in self.ds.type_hist.items():     # well type at the time of the reading (type_history), else the current type
            mk = i.asset_id == w
            for h in hist:
                end = pd.Timestamp(h["to"], tz="UTC") + pd.Timedelta(days=1) if h.get("to") else pd.Timestamp.max.tz_localize("UTC")
                sel = mk & (i.ts >= pd.Timestamp(h["from"], tz="UTC")) & (i.ts < end)
                thr[sel] = self.ds.rules["producing_delta"].get(h["well_type"], thr[sel])
        i["threshold"] = thr
        i["producing"] = i["delta"] >= thr
        self._inspections_cache = (sig, i, self.overlay_conflicts)
        return i

    def latest(self, ids=None):
        i = self.inspections()
        if ids is not None:
            i = i[i.asset_id.isin(ids)]
        i = i[i.ts <= TODAY + pd.Timedelta(days=1)]
        return i.sort_values("ts").groupby("asset_id").tail(1).set_index("asset_id", drop=False)

    def uname(self, uid):
        return self.ds.user_name.get(uid, uid)

    # ---------- notes / reasons ----------
    def active_notes(self, well):
        n = self.ds.n[self.ds.n.asset_id == well]
        out = []
        for _, r in n.iterrows():
            vf = pd.Timestamp(r["valid_from"], tz="UTC") if isinstance(r.get("valid_from"), str) else None
            vt = pd.Timestamp(r["valid_to"], tz="UTC") if isinstance(r.get("valid_to"), str) else None
            if r["note_type"] == "correction":
                continue
            if vf is not None and vf > TODAY:
                continue
            if vt is not None and vt < TODAY.normalize() - pd.Timedelta(days=0):
                continue
            out.append({"id": r["note_id"], "by": self.uname(r["author_user_id"]), "type": r["note_type"],
                        "text": r["text"], "valid_from": r["valid_from"] if isinstance(r.get("valid_from"), str) else None,
                        "valid_to": r["valid_to"] if isinstance(r.get("valid_to"), str) else None})
        return out

    def open_repairs(self, well):
        m = self.ds.m[(self.ds.m.asset_id == well) & (self.ds.m.ts <= TODAY)]
        m = m[pd.to_datetime(m.completed_at, utc=True) > TODAY]
        return m

    def shared_facts(self, well):
        """Runtime-collected shared knowledge for a well (including type/fleet scoped notes)."""
        out = []
        for f in self.mem.facts():
            if f["kind"] in ("note", "claim") and (
                    (f["scope_type"] == "well" and f["scope_id"] == well)):
                out.append(f)
        return out

    # ---------- tools ----------
    def well_status(self, well):
        L = self.latest([well])
        if L.empty:
            return {"error": f"No inspections for {well}"}
        r = L.iloc[0]
        meta = self.ds.w.loc[well]
        notes = self.active_notes(well)
        repairs = self.open_repairs(well)
        shared = self.shared_facts(well)
        src = self.ds.rules["prov"].get(f"producing_delta:{r.well_type}", f"OM-{r.well_type}")
        cites = [r.inspection_id, src] + [n["id"] for n in notes] + list(repairs.maintenance_id)
        card = {
            "well": well, "name": meta["name"], "type": r.well_type, "area": self.ds.area_name.get(meta["area_id"]),
            "producing": bool(r.producing), "inspection": r.inspection_id, "inspected_at": str(r.ts.date()),
            "inspected_by": self.uname(r.inspector_user_id), "method": r.method,
            "wellhead_temp_c": r.wellhead_temp_c, "ambient_temp_c": r.ambient_temp_c,
            "delta_c": round(float(r.delta), 1), "threshold_c": r.threshold, "threshold_source": src,
            "recorded_status": meta["recorded_status"], "inspector_note": r.notes,
            "correction": r.correction, "original_wellhead_temp_c": r.orig_wellhead_temp_c,
            "notes": notes, "open_repairs": [
                {"id": m.maintenance_id, "issue": m.issue, "started": m.started_at[:10], "planned_end": m.completed_at[:10]}
                for m in repairs.itertuples()],
            "shared_facts": [{"by": f["author"], "text": f["text"], "status": f["status"], "valid_from": f["valid_from"], "valid_to": f["valid_to"]} for f in shared],
        }
        stale = (meta["recorded_status"] == "active") != bool(r.producing)
        card["recorded_status_stale"] = bool(stale)
        return {"visual": "card", "rows": [card], "citations": cites, "notes": []}

    def wells_not_producing(self, area=None, well_type=None):
        ids = self.wells_in(area=area, well_type=well_type)
        L = self.latest(ids)
        L = L[~L.producing]
        rows = []
        cites = []
        for w, r in L.iterrows():
            repairs = self.open_repairs(w)
            notes = self.active_notes(w)
            shared = [f for f in self.shared_facts(w)]
            reasons = []
            if len(repairs):
                for m in repairs.itertuples():
                    reasons.append(f"Repair {m.maintenance_id}: {m.issue}, started {m.started_at[:10]}, still open")
                    cites.append(m.maintenance_id)
            for n in notes:
                reasons.append(f"Note {n['id']} ({n['by']}): {n['text']}")
                cites.append(n["id"])
            for f in shared:
                reasons.append(f"Shared note by {f['author']} [{f['status']}]: {f['text']}")
            rows.append({
                "Well": w, "Wellhead above air (°C)": round(float(r.delta), 1),
                "Recorded status": meta_status(self.ds.w.loc[w, "recorded_status"], False),
                "Last inspected": str(r.ts.date()),
                "Reason": "; ".join(reasons) if reasons else
                          f"No recorded reason. Inspector noted: \"{r.notes}\". Suggest a field check." if r.notes else
                          "No recorded reason. Suggest a field check.",
                "Correction": r.correction or "",
            })
            cites.append(r.inspection_id)
        rows.sort(key=lambda x: x["Well"])
        # also report wells excluded because of a correction
        excl = []
        raw = self.ds.i[self.ds.i.asset_id.isin(ids)].sort_values("ts").groupby("asset_id").tail(1).set_index("asset_id")
        raw["prod_raw"] = raw.delta >= raw.well_type.map(self.ds.rules["producing_delta"])
        eff = self.latest(ids)
        for w in raw.index:
            if (not raw.loc[w, "prod_raw"]) and bool(eff.loc[w, "producing"]):
                excl.append(f"{w} is no longer listed: its latest reading was corrected ({eff.loc[w, 'correction']}).")
                cites.append(eff.loc[w, "inspection_id"])
        return {"visual": "table", "rows": rows, "citations": sorted(set(cites)), "notes": excl}

    def timeseries(self, well, weeks=13):
        i = self.inspections()
        i = i[(i.asset_id == well) & (i.ts <= TODAY + pd.Timedelta(days=1))].sort_values("ts").tail(int(weeks))
        rows = [{"date": str(r.ts.date()), "wellhead_temp_c": r.wellhead_temp_c, "ambient_temp_c": r.ambient_temp_c,
                 "delta_c": round(float(r.delta), 1), "producing": bool(r.producing), "inspection": r.inspection_id}
                for r in i.itertuples()]
        return {"visual": "line", "rows": rows, "citations": list(i.inspection_id),
                "notes": [f"Not producing on: {', '.join(r['date'] for r in rows if not r['producing']) or 'none'}"]}

    def _spill_df(self, ids, start, end):
        i = self.inspections()
        s = i[i.asset_id.isin(ids) & i.spill_detected & (i.ts >= start) & (i.ts <= end)].copy()
        return s

    def spills(self, area=None, well=None, wells=None, days=None, months=None, year=None, start=None, end=None,
               reportable_only=False, group_by=None):
        ids = self.wells_in(well=well, wells=wells, area=area)
        a, b = self.period(days, months, None, year, start, end)
        s = self._spill_df(ids, a, b)
        if reportable_only:
            s = s[s.spill_est_volume_bbl >= self.ds.rules["reportable_bbl"]]
        if group_by == "area_month":
            s["month"] = s.ts.dt.strftime("%b")
            months_ = sorted({m: pd.Timestamp(f"2000-{m}-01").month for m in s.month}.items(), key=lambda x: x[1])
            order = [m for m, _ in months_]
            rows = []
            for aid, name in self.ds.area_name.items():
                if aid not in set(self.ds.w.loc[ids, "area_id"]):
                    continue
                sub = s[s.area_id == aid]
                row = {"Area": name}
                for m in order:
                    row[m] = int((sub.month == m).sum())
                row["Total"] = int(len(sub))
                rows.append(row)
            return {"visual": "heatmap", "rows": rows, "months": order, "citations": [], "notes": [
                "Corrected detections (e.g. rainwater) are excluded."]}
        rows = []
        for r in s.sort_values("ts").itertuples():
            meta = self.ds.w.loc[r.asset_id]
            rows.append({"Well": r.asset_id, "Date": str(r.ts.date()), "Barrels": r.spill_est_volume_bbl,
                         "Area %": r.spill_area_pct, "Inspection": r.inspection_id,
                         "lat": meta["lat"], "lon": meta["lon"],
                         "Class": self.spill_class(r.spill_est_volume_bbl),
                         "Note": r.correction or ""})
        total = round(float(s.spill_est_volume_bbl.sum()), 1)
        notes = [f"{len(rows)} spills, {total} bbl total."]
        if reportable_only:                      # does a written notice exist, and is it late?
            for r in s.sort_values("ts").itertuples():
                f = self.ds.r[(self.ds.r.related_inspection_id == r.inspection_id) & (self.ds.r.event_type == "spill_report_filed")]
                lim = self.ds.report_limit(r.ts)
                due = r.ts + pd.Timedelta(hours=lim)
                if len(f):
                    h_ = float(f.iloc[0].hours_to_report)
                    notes.append(f"{r.asset_id} ({r.inspection_id}, {r.spill_est_volume_bbl} bbl): written notice filed after {h_:g} h ({'on time' if h_ <= lim else f'LATE vs {lim:g} h'}), {f.iloc[0].event_id}.")
                else:
                    notes.append(f"{r.asset_id} ({r.inspection_id}, {r.spill_est_volume_bbl} bbl): reportable, NO written notice on record; it was due by {due:%Y-%m-%d %H:%M}" + (" so it is OVERDUE." if due < TODAY else "."))
            if not len(s): notes.append("No spill in this period reached the reportable threshold.")
            else: notes.append("No other spill in this period reached the reportable threshold (5 bbl).")
        i2 = self.inspections()
        corr = i2[i2.asset_id.isin(ids) & i2.orig_spill_detected & ~i2.spill_detected & (i2.ts >= a) & (i2.ts <= b)]
        for c in corr.itertuples():
            notes.append(f"Excluded {c.inspection_id} ({c.ts.date()}): corrected, {c.correction}")
        return {"visual": "table", "rows": rows, "total_bbl": total, "count": len(rows),
                "citations": list(s.inspection_id) + list(corr.inspection_id), "notes": notes}

    def spill_class(self, v):
        R = self.ds.rules
        if v is None or pd.isna(v):
            return "unknown"
        if v >= R["major_bbl"]:
            return "major"
        if v >= R["reportable_bbl"]:
            return "reportable"
        if v >= 1:
            return "moderate"
        return "minor"

    def downtime(self, area=None, well=None, wells=None, well_type=None, days=None, months=None, year=None,
                 start=None, end=None, top_n=None):
        ids = self.wells_in(well=well, wells=wells, area=area, well_type=well_type)
        a, b = self.period(days, months, None, year, start, end)
        i = self.inspections()
        i = i[i.asset_id.isin(ids) & (i.ts >= a) & (i.ts <= b) & ~i.producing]
        g = i.groupby("asset_id").agg(weeks=("inspection_id", "count"), ids=("inspection_id", list))
        rows = [{"Well": w, "Downtime (days)": int(r.weeks) * WEEK_DAYS, "Type": self.ds.w.loc[w, "well_type"],
                 "Inspections": r.ids} for w, r in g.iterrows()]
        rows.sort(key=lambda x: (-x["Downtime (days)"], x["Well"]))
        cites = [x for r in rows[: (top_n or len(rows))] for x in r["Inspections"]]
        if top_n:
            rows = rows[: int(top_n)]
        for r in rows:
            r["Inspections"] = len(r["Inspections"])
        vis = "bar" if (top_n or len(rows) > 1) else "text"
        notes = [f"Window {a.date()} to {b.date()}; each non-producing weekly inspection counts 7 days."]
        if len(ids) == 1 and len(i):                    # one well: say WHICH inspections, why they count, and the repairs around them
            for r in i.sort_values("ts").itertuples():
                m_ = self.ds.m   # corrective repairs in progress around this inspection (started up to 4 days before, still running or started within 10 days after)
                near = m_[(m_.asset_id == r.asset_id) & (m_.maintenance_type == "corrective") & (m_.ts <= r.ts + pd.Timedelta(days=10)) & (pd.to_datetime(m_.completed_at, utc=True) >= r.ts - pd.Timedelta(days=4))]
                hot = f" (wellhead {r.wellhead_temp_c:g} °C looks hot, but air was {r.ambient_temp_c:g} °C: only {r.delta:.1f} °C above air, limit {r.threshold:g} °C)" if r.wellhead_temp_c > 45 else f" ({r.delta:+.1f} °C vs air, limit {r.threshold:g} °C)"
                notes.append(f"Not producing on {r.ts.date()} ({r.inspection_id}){hot}" + (f"; repair {', '.join(near.maintenance_id)}: {'; '.join(near.issue)}" if len(near) else ""))
                cites += list(near.maintenance_id)
        return {"visual": vis, "rows": rows, "citations": cites, "notes": notes}

    def repair_costs(self, wells, year=None, days=None, months=None, start=None, end=None, corrective_only=False):
        a, b = self.period(days, months, None, year, start, end)
        m = self.ds.m
        m = m[m.asset_id.isin(wells) & (m.ts >= a) & (m.ts <= b)]
        if corrective_only:
            m = m[m.maintenance_type == "corrective"]
        rows = []
        for w in wells:
            sub = m[m.asset_id == w]
            rows.append({"Well": w, "Total cost (USD)": int(sub.cost_total.sum()), "Repairs": int(len(sub))})
        return {"visual": "table", "rows": rows, "citations": list(m.maintenance_id),
                "notes": [f"Repairs started {a.date()} to {b.date()}."]}

    def rca_candidates(self, area=None, equipment="pump_jack", months=12, well_type=None):
        ids = self.wells_in(area=area, well_type=well_type)
        a = (ANCHOR - DateOffset(months=int(months))).normalize()
        m = self.ds.m
        m = m[m.asset_id.isin(ids) & (m.maintenance_type == "corrective") & (m.equipment_kind == equipment)
              & (m.ts >= a) & (m.ts <= TODAY + pd.Timedelta(days=1))]
        overrides = {}
        for f in self.mem.facts(kind="rule"):
            if f["field"] == "rca_count" and f["scope_type"] == "well_type":
                overrides[f["scope_id"]] = (int(float(f["corrected"])), f["author"])
        rows, notes, cites = [], [], []
        for w, sub in m.groupby("asset_id"):
            wt = self.ds.w.loc[w, "well_type"]
            thr = self.ds.rules["rca_count"].get(wt, 3)
            src = "manual"
            if wt in overrides:
                thr, who = overrides[wt]
                src = f"rule set by {who}"
            if len(sub) >= thr:
                rows.append({"Well": w, "Type": wt, "Corrective repairs (12 mo)": int(len(sub)),
                             "Threshold": thr, "Source": src, "Repairs": ", ".join(sub.maintenance_id)})
                cites += list(sub.maintenance_id)
        rows.sort(key=lambda x: x["Well"])
        for wt, (v, who) in overrides.items():
            notes.append(f"Threshold for {wt} wells is {v} repairs by {who}'s rule (manual says {self.ds.rules['rca_count'].get(wt)}).")
        return {"visual": "table", "rows": rows, "citations": sorted(set(cites)) + ["OM-T200 §10"], "notes": notes}

    def compliance(self, well=None, area=None, months=12, days=None, start=None, end=None, spill_filter=None):
        """Evaluate SOP protocols per real spill + open actions. Returns breaches and pending items."""
        R = self.ds.rules
        ids = self.wells_in(well=well, area=area)
        a, b = self.period(days, months if not days else None, None, None, start, end)
        i = self.inspections()
        s = i[i.asset_id.isin(ids) & i.spill_detected & (i.ts >= a) & (i.ts <= b)]
        rows, pending, cites = [], [], []
        reg = self.ds.r
        for r in s.sort_values("ts").itertuples():
            vol = r.spill_est_volume_bbl
            klass = self.spill_class(vol)
            ev = reg[reg.related_inspection_id == r.inspection_id]
            m = self.ds.m[self.ds.m.triggered_by_inspection_id == r.inspection_id]
            ch = None
            for x in m.itertuples():
                if pd.notna(x.contain_hours):
                    ch = (x.maintenance_id, x.contain_hours)
            reportable = klass in ("reportable", "major")
            limit_h = R["major_report_hours"] if klass == "major" else self.ds.report_limit(r.ts)
            if reportable:
                filed = ev[ev.event_type == "spill_report_filed"]
                if len(filed):
                    h = float(filed.iloc[0].hours_to_report)
                    if h > limit_h:
                        rows.append(dict(Well=r.asset_id, Protocol="SR-01", Spill=r.inspection_id, Date=str(r.ts.date()),
                                         Volume=vol, Finding=f"Reported after {h:g} h vs {limit_h:g} h limit",
                                         Evidence=filed.iloc[0].event_id))
                        cites.append(filed.iloc[0].event_id)
                elif r.ts + pd.Timedelta(hours=limit_h) < TODAY:
                    rows.append(dict(Well=r.asset_id, Protocol="SR-01", Spill=r.inspection_id, Date=str(r.ts.date()),
                                     Volume=vol, Finding=f"Possible breach: reportable ({vol} bbl) but no written notice on record; "
                                                         f"was due within {limit_h:g} h of discovery",
                                     Evidence=r.inspection_id))
            if ch and ch[1] > R["contain_hours"]:
                rows.append(dict(Well=r.asset_id, Protocol="SR-02", Spill=r.inspection_id, Date=str(r.ts.date()),
                                 Volume=vol, Finding=f"Contained after ~{ch[1]:g} h vs {R['contain_hours']:g} h limit",
                                 Evidence=ch[0]))
                cites.append(ch[0])
            if reportable:
                due = r.ts + pd.Timedelta(days=R["verify_days"])
                closed = ev[(ev.event_type == "site_inspection") & (ev.status == "closed")]
                if not len(closed):
                    open_ev = ev[ev.event_type == "site_inspection"]
                    ref = open_ev.iloc[0].event_id if len(open_ev) else r.inspection_id
                    item = dict(Well=r.asset_id, Protocol="SR-03", Spill=r.inspection_id, Date=str(r.ts.date()), Volume=vol,
                                Finding=f"Clean-up verification due {due.date()}, not closed", Evidence=ref)
                    (rows if due < TODAY else pending).append(item)
            for nov in ev[ev.event_type == "notice_of_violation"].itertuples():
                resp = reg[(reg.asset_id == r.asset_id) & (reg.event_type == "nov_response_filed")
                           & (reg.related_inspection_id == r.inspection_id)]
                due = nov.ts + pd.Timedelta(days=R["nov_days"])
                if not len(resp) and nov.status != "closed":
                    item = dict(Well=r.asset_id, Protocol="RC-04", Spill=r.inspection_id, Date=str(nov.ts.date()), Volume=vol,
                                Finding=f"Notice of violation {nov.event_id} (fine USD {int(nov.fine_usd)}) needed a response by "
                                        f"{due.date()}; none recorded, status {nov.status}", Evidence=nov.event_id)
                    (rows if due < TODAY else pending).append(item)
            cites.append(r.inspection_id)
        # RCA pending (pump_jack/flowline etc.)
        for w in ids:
            m = self.ds.m[(self.ds.m.asset_id == w) & (self.ds.m.maintenance_type == "corrective")
                          & (self.ds.m.ts >= (ANCHOR - DateOffset(months=12)).normalize()) & (self.ds.m.ts <= TODAY)]
            thr = self.ds.rules["rca_count"].get(self.ds.w.loc[w, "well_type"], 3)
            for ek, sub in m.groupby("equipment_kind"):
                if len(sub) >= thr:
                    pending.append(dict(Well=w, Protocol="Manual §10", Spill="", Date="", Volume="",
                                        Finding=f"Root-cause analysis due: {len(sub)} corrective {ek} repairs in 12 months",
                                        Evidence=", ".join(sub.maintenance_id)))
        fines = reg[reg.asset_id.isin(ids) & (reg.status == "open") & (reg.fine_usd > 0)]
        notes = [f"Open fines: USD {int(fines.fine_usd.sum())}" if len(fines) else "No open fines."]
        for w in ids:
            for n in self.active_notes(w):
                if "maintenance system" in n["text"].lower():
                    pending.append(dict(Well=w, Protocol="Manual §4", Spill="", Date="", Volume="",
                                        Finding=f"Planned shut-in not yet recorded in the maintenance system ({n['id']})",
                                        Evidence=n["id"]))
        return {"visual": "table", "rows": rows, "pending": pending, "citations": sorted(set(cites)), "notes": notes}

    def spills_over_containment(self, area, days=90):
        a, b = self.period(days=days)
        ids = self.wells_in(area=area)
        s = self._spill_df(ids, a, b)
        rows, cites = [], []
        for r in s.itertuples():
            for x in self.ds.m[self.ds.m.triggered_by_inspection_id == r.inspection_id].itertuples():
                if pd.notna(x.contain_hours) and x.contain_hours > self.ds.rules["contain_hours"]:
                    rows.append({"Well": r.asset_id, "Date": str(r.ts.date()), "Inspection": r.inspection_id,
                                 "Report": x.maintenance_id, "Contained after (h)": x.contain_hours,
                                 "Limit (h)": self.ds.rules["contain_hours"]})
                    cites += [r.inspection_id, x.maintenance_id]
        return {"visual": "table", "rows": rows, "citations": cites, "notes": []}


def meta_status(rec, producing):
    """Mark recorded status when it disagrees with inspections."""
    return rec + (" (out of date)" if (rec == "active") != producing else "")


def _spill_check(self, well, date=None):
    i = self.inspections()
    i = i[(i.asset_id == well) & (i.orig_spill_detected)]
    if date:
        d = pd.Timestamp(date, tz="UTC")
        i = i[(i.ts - d).abs() <= pd.Timedelta(days=3)]
    if i.empty:
        return {"visual": "text", "rows": [], "citations": [], "notes": [f"No spill detection found for {well}" + (f" near {date}" if date else "")]}
    r = i.sort_values("ts").iloc[-1] if not date else i.iloc[(i.ts - pd.Timestamp(date, tz="UTC")).abs().argsort()].iloc[0]
    notes = self.ds.n[(self.ds.n.asset_id == well)]
    rel = notes[notes.text.str.contains(r.inspection_id, regex=False) |
                ((notes.ts - r.ts).abs() <= pd.Timedelta(days=14)) & (notes.note_type != "correction")]
    maint = self.ds.m[self.ds.m.triggered_by_inspection_id == r.inspection_id]
    corrected = bool(r.orig_spill_detected and not r.spill_detected)
    return {"visual": "card", "rows": [{
        "well": well, "inspection": r.inspection_id, "date": str(r.ts.date()), "volume_bbl": r.spill_est_volume_bbl,
        "ai_estimate_bbl": r.orig_spill_volume, "inspector_note": r.notes, "formally_corrected": corrected,
        "correction": r.correction, "repair": [f"{m.maintenance_id}: {m.issue}" for m in maint.itertuples()],
        "notes": [{"id": n.note_id, "by": self.uname(n.author_user_id), "type": n.note_type, "text": n.text} for n in rel.itertuples()],
    }], "citations": [r.inspection_id] + list(rel.note_id) + list(maint.maintenance_id), "notes": [
        "Neither informal note is a formal correction; the detection stands." if not corrected else "Detection was formally corrected."]}
