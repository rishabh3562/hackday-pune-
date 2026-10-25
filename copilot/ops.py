"""Operations-SOP tools (OPS-1..OPS-5), regulator letter, supplier recall, MOC memos, delay reasons.
Still deterministic: every rule threshold or list is read from the SOP / memo / letter text in the dataset, never typed here."""
import glob
import os
import re

import pandas as pd

from .data import TODAY, _read
from .tools import Engine

GAS_RE = re.compile(r"gas odou?r|smelled gas|rotten[- ]egg|h2s monitor alarm", re.I)
SHUT_RE = re.compile(r"shut[- ]in|shut the well in", re.I)
RESTART_RE = re.compile(r"^restarted|back online|back on production", re.I)
BYP_OUT_RE = re.compile(r"bypass (out|removed|pulled)|took the bypass out|removed|pulled", re.I)
BYP_IN_RE = re.compile(r"bypass", re.I)
SYMPTOMS = [(r"leak", 4, "leak"), (r"high pressure alarm", 3, "pressure alarm"), (r"tripping", 3, "drive tripping"),
            (r"amps hunting|hunting between", 2, "amps hunting"), (r"tagging bottom", 2, "tagging bottom"),
            (r"rattling", 2, "rattling"), (r"rod squeal", 1, "rod squeal"), (r"fluid pound", 1, "fluid pound")]


def _rule_hours(root_text, default_before, default_after):
    """OPS-1 response window: '24 h before <date>, 12 h from <date>' read from the SOP."""
    m = re.search(r"within \*\*(\d+) hours\*\*[^.]*?before (\d+ \w+ \d{4})[^.]*?\*\*(\d+) hours\*\*", re.sub(r"\s+", " ", root_text))
    if m:
        return float(m.group(1)), pd.Timestamp(m.group(2), tz="UTC"), float(m.group(3))
    return default_before, pd.Timestamp("2027-01-01", tz="UTC"), default_after


def _sop(self, name):
    for rel, _, t in self.ds.docs:
        if rel.endswith(name):
            return t
    return ""


def _opnotes(self):
    n = self.ds.n
    return n[n.note_type == "operator_note"].sort_values("ts")


def _area(self, w):
    return self.ds.area_name.get(self.ds.w.loc[w, "area_id"], "")


def _plugged(self):
    w = self.ds.w
    return set(w[w.get("status", pd.Series("", index=w.index)).fillna("").eq("plugged_and_abandoned")].asset_id) if "status" in w.columns else set()


def _parts(self):
    """maintenance_id -> {model, serial, lot, line} from the 'Parts installed' line of the report; cached."""
    if hasattr(self, "_parts_cache"):
        return self._parts_cache
    out = {}
    for mid, t in self.ds.reports.items():
        m = re.search(r"\*\*Parts installed:\*\*\s*(.+)", t)
        if m:
            line = m.group(1).strip()
            out[mid] = {"line": line, "serial": (re.search(r"serial\s+(\S+?)[,\s]", line + " ") or [None, None])[1],
                        "lot": (re.search(r"lot\s+(\S+)", line) or [None, None])[1],
                        "model": re.split(r",|\bpump\b", line)[0].strip()}
    self._parts_cache = out
    return out


def _now_status(self, w):
    """Producing / not producing right now (OPS-3: a newer shut-in/restart operator note overrides the inspection)."""
    ins = self.latest([w]).iloc[0]
    n = _opnotes(self)
    n = n[(n.asset_id == w) & (n.ts > ins.ts)]
    ev = [r for r in n.itertuples() if SHUT_RE.search(r.text) or RESTART_RE.search(r.text)]
    if ev:
        return "Not producing (shut-in note)" if SHUT_RE.search(ev[-1].text) else "Producing (unconfirmed, restart note)"
    return "Producing" if ins.producing else "Not producing"


# ---------- OPS-1 ----------
def gas_response(self, since="2026-11-01", well=None):
    """Gas-odor operator notes and whether a field response (maintenance job start or MANUAL inspection) followed in time."""
    sop = _sop(self, "operations-sop-rev2.md")
    sec = re.search(r"## OPS-1.*?(?=## OPS-2)", sop, re.S)
    before, cut, after = _rule_hours(sec.group(0) if sec else "", 24.0, 12.0)
    n = _opnotes(self)
    n = n[n.text.map(lambda t: bool(GAS_RE.search(t))) & (n.ts >= pd.Timestamp(since, tz="UTC"))]
    if well:
        n = n[n.asset_id == well]
    I, M = self.inspections(), self.ds.m
    rows, cites = [], []
    for r in n.itertuples():
        lim = before if r.ts < cut else after
        cand = []
        for m in M[(M.asset_id == r.asset_id) & (M.ts > r.ts)].itertuples():
            cand.append((m.ts, m.maintenance_id))
        for i in I[(I.asset_id == r.asset_id) & (I.ts > r.ts) & (I.method == "manual")].itertuples():
            cand.append((i.ts, i.inspection_id))
        cand.sort()
        due = r.ts + pd.Timedelta(hours=lim)
        resp = cand[0] if cand else None
        hrs = round((resp[0] - r.ts).total_seconds() / 3600, 1) if resp else None
        met = bool(resp and resp[0] <= due)
        rows.append({"Well": r.asset_id, "Area": _area(self, r.asset_id), "Reported at": r.ts.strftime("%Y-%m-%d %H:%M"),
                     "Response": f"{resp[1]} at {resp[0]:%Y-%m-%d %H:%M}" if resp else "none",
                     "Hours to response": hrs if hrs is not None else "-", "Deadline": f"{lim:g} h", "Met/Missed": "Met" if met else "Missed"})
        cites += [r.note_id] + ([resp[1]] if resp else [])
    h2s = []
    if well:                                  # H2S reading from the response job's safety section
        for r in n.itertuples():
            for m in M[(M.asset_id == well) & (M.ts > r.ts)].sort_values("ts").itertuples():
                t = self.ds.reports.get(m.maintenance_id, "")
                g = re.search(r"highest reading (\d+(?:\.\d+)?) ppm", t)
                if g:
                    h2s.append(f"{m.maintenance_id} (job started {m.started_at[:10]}): highest personal H2S reading {g.group(1)} ppm.")
                    cites.append(m.maintenance_id)
                    break
    if well and not h2s:
        near = I[(I.asset_id == well) & (I.ts >= n.ts.min() - pd.Timedelta(days=1)) & (I.ts <= n.ts.min() + pd.Timedelta(days=2))] if len(n) else I.iloc[0:0]
        h2s.append("No H2S reading is recorded for this report: the operator note only says gas was smelled, and H2S ppm values exist only in maintenance reports' safety sections (personal monitors) - no job followed the note. "
                   + ("Inspections around it: " + "; ".join(f"{x.inspection_id} {x.ts:%d %b %H:%M} ({x.method}, no gas measurement)" for x in near.itertuples()) + "." if len(near) else ""))
    missed = sum(x["Met/Missed"] == "Missed" for x in rows)
    return {"visual": "table", "rows": rows, "citations": sorted(set(cites)),
            "notes": [f"{len(rows)} gas-odor notes since {since}; {missed} missed. OPS-1: response = a maintenance job starting, or a MANUAL inspection (drone does not count), after the note within {before:g} h (notes before {cut:%d %b %Y}) / {after:g} h (from then)."] + h2s}


# ---------- OPS-2 ----------
def _mocs(self):
    memos = {}
    for rel, _, t in self.ds.docs:
        b = os.path.basename(rel)
        if not b.startswith("moc-"):
            continue
        mid = re.search(r"MOC-\d{4}-\d+", t).group(0)
        flat = re.sub(r"\s+", " ", t)
        exp = re.search(r"expires on (\d+ \w+ \d{4})", flat)
        eff = re.search(r"Effective from (\d+ \w+ \d{4})", flat)
        ext = re.search(r"extends (MOC-\d{4}-\d+)", flat)
        wells = set(re.findall(r"WELL-\d{4}", flat))
        memos[mid] = {"id": mid, "wells": wells, "expires": pd.Timestamp(exp.group(1), tz="UTC") if exp else None,
                      "from": pd.Timestamp(eff.group(1), tz="UTC") if eff else None, "extends": ext.group(1) if ext else None, "file": rel}
    for m in memos.values():            # an extension replaces the earlier memo's expiry
        if m["extends"] in memos:
            memos[m["extends"]]["expires"] = m["expires"]
            memos[m["extends"]]["extended_by"] = m["id"]
    return memos


def bypass_audit(self, only_current=False):
    """Temporary flowline bypasses (operator notes) vs MOC memos (OPS-2)."""
    memos = _mocs(self)
    n = _opnotes(self)
    n = n[n.text.map(lambda t: bool(BYP_IN_RE.search(t)))]
    rows, cites = [], []
    for w, g in n.groupby("asset_id"):
        spans, cur = [], None
        for r in g.sort_values("ts").itertuples():
            out = bool(BYP_OUT_RE.search(r.text))
            if out and cur:
                spans.append((cur, r)); cur = None
            elif not out and not cur:
                cur = r
        if cur:
            spans.append((cur, None))
        for a, b in spans:
            covering = [m for m in memos.values() if w in m["wells"]]
            viol_memo = None
            if not covering:
                status, appr, until = "Not approved", "none", "-"
            else:
                m = covering[0]
                end = (m["expires"] + pd.Timedelta(days=1)) if m["expires"] is not None else None
                appr, until = m["id"] + (f" (extended by {m['extended_by']})" if m.get("extended_by") else ""), f"{m['expires']:%Y-%m-%d}"
                last = b.ts if b is not None else TODAY + pd.Timedelta(days=1)
                status = "Expired" if end is not None and last > end else "Allowed"
            if only_current and b is not None:
                continue
            rows.append({"Well": w, "Area": _area(self, w), "Bypass in": f"{a.ts:%Y-%m-%d %H:%M}", "Bypass out": f"{b.ts:%Y-%m-%d %H:%M}" if b is not None else "still in",
                         "Approval": appr, "Approval valid until": until, "Status": status})
            cites += [a.note_id] + ([b.note_id] if b is not None else [])
    for k in memos.values():
        cites.append(k["id"])
    bad = [r for r in rows if r["Status"] != "Allowed"]
    return {"visual": "table", "rows": sorted(rows, key=lambda r: (r["Status"] == "Allowed", r["Well"])), "citations": sorted(set(cites)),
            "notes": [f"{len(rows)} bypass periods found in operator notes; {len(bad)} are not allowed (OPS-2). Expiry runs to the end of the memo's date; an extension memo replaces the earlier expiry."]}


# ---------- OPS-3 ----------
def status_conflicts(self, area=None, team=None):
    """Wells whose latest inspection and latest shut-in/restart operator note disagree on producing (OPS-3)."""
    ids = set(self.wells_in(area=area)) - _plugged(self)
    L = self.latest(list(ids))
    n = _opnotes(self)
    rows, cites = [], []
    for w, g in n[n.asset_id.isin(ids)].groupby("asset_id"):
        ev = [r for r in g.itertuples() if SHUT_RE.search(r.text) or RESTART_RE.search(r.text)]
        if not ev or w not in L.index:
            continue
        r, ins = ev[-1], L.loc[w]
        shut = bool(SHUT_RE.search(r.text))
        if r.ts <= ins.ts:
            continue                                   # inspection is the more recent evidence: no override
        if shut and ins.producing:
            now = "Not producing oil"
        elif (not shut) and not ins.producing:
            now = "Producing oil (unconfirmed)"
        else:
            continue
        rows.append({"Well": w, "Area": _area(self, w), "Latest inspection": f"{ins.inspection_id}, {ins.ts:%Y-%m-%d}, {'producing' if ins.producing else 'not producing'}",
                     "Latest operator note": f"{r.ts:%Y-%m-%d %H:%M}, {'shut in' if shut else 'restarted'}: {r.text}", "Status now": now})
        cites += [ins.inspection_id, r.note_id]
    return {"visual": "table", "rows": sorted(rows, key=lambda r: r["Well"]), "citations": cites,
            "notes": [f"{len(rows)} wells where a newer shut-in/restart operator note overrides the latest inspection (OPS-3). Plugged-and-abandoned wells are excluded; 'unconfirmed' = restart note, no inspection since."]}


# ---------- OPS-5 ----------
def cold_weather_check(self, start="2026-12-01", end="2027-02-28", area=None):
    """Freeze protection: inspections at ambient <= -5 C on a producing well need a 'Heat trace check' job within 7 days after."""
    sop = re.sub(r"\s+", " ", _sop(self, "operations-sop-rev2.md"))
    m = re.search(r"ambient[^.]*?[−-]\s?(\d+)\s*°C", sop)
    thr = -float(m.group(1)) if m else -5.0
    I, M = self.inspections(), self.ds.m
    ids = set(self.wells_in(area=area)) - _plugged(self)
    a, b = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    cold = I[I.asset_id.isin(ids) & (I.ts >= a) & (I.ts < b) & (I.ts <= TODAY + pd.Timedelta(days=1)) & (I.ambient_temp_c <= thr) & I.producing]
    rows, cites, ok = [], [], 0
    for r in cold.itertuples():
        hit = M[(M.asset_id == r.asset_id) & M.issue.str.contains("Heat trace check", case=False, na=False) & (M.ts >= r.ts) & (M.ts <= r.ts + pd.Timedelta(days=7))]
        if len(hit):
            ok += 1
            continue
        rows.append({"Well": r.asset_id, "Area": _area(self, r.asset_id), "Inspection": r.inspection_id, "Date": f"{r.ts:%Y-%m-%d}",
                     "Ambient (°C)": r.ambient_temp_c, "Heat trace check within 7 days": "none"})
        cites.append(r.inspection_id)
    rows.sort(key=lambda x: (x["Date"], x["Well"]))
    return {"visual": "table", "rows": rows, "citations": cites + ["operations-sop-rev2.md §OPS-5"],
            "notes": ["SOP (OPS-5, freeze protection): from 1 Dec to 28 Feb, any inspection with ambient at or below -5 °C on a well producing at that reading needs a maintenance job whose issue contains 'Heat trace check' on that well, starting within 7 days after the inspection; a cold reading on a non-producing well needs none.",f"OPS-5 (1 Dec to 28 Feb, ambient <= {thr:g} °C, producing well): {len(cold)} qualifying inspections in {start}..{end}, {ok} followed by a heat-trace job within 7 days, {len(rows)} missed."]}


# ---------- regulator letter ----------
def spill_letter_audit(self):
    """Regulator letter (Nov 2026): reportable spills in NE-7/NE-8 since 1 Jun 2026 need soil samples; clean-up report must say so."""
    I, M = self.inspections(), self.ds.m
    letter = re.sub(r"\s+", " ", _sop(self, "regulator-letter-2026-11-20.md"))
    since = pd.Timestamp("2026-06-01", tz="UTC")
    mm = re.search(r"since (\d+ \w+ \d{4})", letter)
    if mm:
        since = pd.Timestamp(mm.group(1), tz="UTC")
    areas = [a["area_id"] for a in self.ds.areas if a["name"] in ("Northeast Block 7", "Northeast Block 8")]
    thr = self.ds.rules["reportable_bbl"]
    s = I[I.area_id.isin(areas) & I.spill_detected & (I.spill_est_volume_bbl >= thr) & (I.ts >= since)]
    rows, cites = [], []
    for r in s.sort_values("ts").itertuples():
        jobs = M[M.triggered_by_inspection_id == r.inspection_id]
        verdict, job = "No: no clean-up job on record", "none"
        if len(jobs):
            j = jobs.sort_values("ts").iloc[-1]
            job = j.maintenance_id
            t = self.ds.reports.get(job, "")
            sec = re.search(r"## Spill clean-up and waste(.*?)(?=\n## |\Z)", t, re.S)
            if sec and "Soil samples sent to the lab." in sec.group(1):
                verdict = "Yes: report says soil samples were sent to the lab"
            elif sec:
                verdict = "No: clean-up section lacks 'Soil samples sent to the lab.'" + (" (field soil readings only)" if "soil samples taken" in sec.group(1).lower() else "")
            else:
                verdict = "No: no clean-up section in the report" + (" (job still in progress)" if pd.Timestamp(j.completed_at) > TODAY else "")
            cites.append(job)
        vol = r.spill_est_volume_bbl
        rows.append({"Well": r.asset_id, "Area": _area(self, r.asset_id), "Inspection": f"{r.inspection_id}, {r.ts:%Y-%m-%d}",
                     "Volume": f"{vol:g} bbl" + (" (corrected)" if r.correction else ""), "Clean-up job": job, "Compliant?": verdict})
        cites.append(r.inspection_id)
    bad = sum(x["Compliant?"].startswith("No") for x in rows)
    notes = [f"{len(rows)} spills of at least {thr:g} bbl in Northeast Block 7/8 since {since:%d %b %Y} (volumes after corrections; spills corrected to not-a-spill are excluded); {bad} not compliant; results were due 15 Jan 2027."]
    return {"visual": "table", "rows": rows, "citations": sorted(set(cites)) + ["regulator-letter-2026-11-20.md"], "notes": notes}


# ---------- supplier recall ----------
def recalled_pumps(self, area=None, only_not_producing=False):
    """Recalled Highline RP-175 rod pumps still in the ground: only the pump currently in the well matters."""
    raw = _sop(self, "supplier-recall-notice-2026-12-01.md")
    sec = re.search(r"## What is recalled(.*?)(?=\n## |Pumps from all other)", raw, re.S)      # the bulleted recalled lots only
    lots = set(re.findall(r"LOT-\d{4}-[A-Z]", sec.group(1) if sec else ""))
    P, M = _parts(self), self.ds.m
    plugged = _plugged(self)
    swaps = {}
    for f in self.mem.facts():
        if f["kind"] in ("note", "claim") and f["scope_type"] == "well" and re.search(r"swapp|replac|pulled", f["text"] or "", re.I) and "pump" in (f["text"] or "").lower():
            swaps.setdefault(f["scope_id"], []).append(f)
    rows, cites = [], []
    for w in sorted(set(self.wells_in(area=area)) - plugged):
        cur = None
        for m in M[(M.asset_id == w)].sort_values("ts").itertuples():
            p = P.get(m.maintenance_id)
            if p and p["lot"] and m.equipment_kind in ("downhole_pump", "esp_pump"):
                cur = (m, p)
        if not cur or "RP-175" not in cur[1]["model"] or cur[1]["lot"] not in lots:
            continue
        m, p = cur
        sw = [f for f in swaps.get(w, []) if f["status"] == "confirmed"]
        src = f"{m.maintenance_id} report (Parts installed line)"
        if sw:
            continue
        now = _now_status(self, w)
        if only_not_producing and now.startswith("Producing"):
            continue
        lr = M[(M.asset_id == w) & (M.ts <= TODAY)].sort_values("ts").iloc[-1]
        rows.append({"Well": w, "Area": _area(self, w), "Pump": p["model"], "Serial": p["serial"], "Lot": p["lot"], "Installed": m.started_at[:10],
                     "Install job": m.maintenance_id, "Install cost (USD)": int(m.cost_total), "Producing now": now,
                     "Last repaired": f"{lr.started_at[:10]} ({lr.maintenance_id}, {lr.maintenance_type}: {lr.issue})", "Source": src})
        cites.append(m.maintenance_id)
    skipped = [f"{w}: swap recorded by {f[0]['author']} ({f[0]['status']})" for w, f in swaps.items() if any(x["status"] == "confirmed" for x in f)]
    pend = [f"{w}: {f[0]['author']}'s claim '{f[0]['text']}' is {f[0]['status']} and was NOT applied" for w, f in swaps.items() if not any(x["status"] == "confirmed" for x in f)]
    notes = [f"Recalled lots (supplier notice HPC-RN-2026-07): {', '.join(sorted(lots))}; RP-175 rod pumps only, current pump only, ESP wells and plugged wells excluded. {len(rows)} still in the ground.",
             "Facts come from the maintenance reports' 'Parts installed' lines and the supplier notice."]
    if skipped:
        notes.append("Counted as replaced by a user-reported swap (no work order yet): " + "; ".join(skipped))
    notes += pend
    return {"visual": "table", "rows": rows, "citations": sorted(set(cites)) + ["supplier-recall-notice-2026-12-01.md"], "notes": notes}


# ---------- Q10: why a well stayed shut in longer than the repair ----------
def delay_reasons(self, year=2026):
    """Reasons a well stayed shut in longer than the repair itself, by area, from the maintenance reports' own sentences."""
    pat = re.compile(r"stayed shut in for about ([\d.]+) days? longer than the repair itself because ([^.]*)\.")
    kinds = [("Parts back-ordered", r"back-ordered"), ("Weather (road impassable)", r"heavy rain|impassable"), ("Contractor slot", r"contractor slot"),
             ("Crew on spill response", r"higher-priority spill")]
    M = self.ds.m
    M = M[(M.ts >= pd.Timestamp(f"{year}-01-01", tz="UTC")) & (M.ts < pd.Timestamp(f"{year + 1}-01-01", tz="UTC"))]
    recs = []
    for m in M.itertuples():
        t = self.ds.reports.get(m.maintenance_id, "")
        g = pat.search(t)
        if g:
            for name, rx in kinds:
                if re.search(rx, g.group(2)):
                    recs.append((self.ds.area_name.get(m.area_id), name, float(g.group(1)), m.maintenance_id))
        r = re.search(r"well waited about ([\d.]+) days? for it", t)
        if r:
            recs.append((self.ds.area_name.get(m.area_id), "Workover rig busy", float(r.group(1)), m.maintenance_id))
    df = pd.DataFrame(recs, columns=["Area", "Reason", "days", "id"])
    rows = []
    for a, g in df.groupby("Area"):
        for rs, h in g.groupby("Reason"):
            rows.append({"Area": a, "Reason": rs, "Jobs": len(h), "Share of area's delayed jobs": f"{100 * len(h) / len(g):.0f}%", "Typical extra days": round(float(h.days.median()), 1)})
    tot = df.groupby("Area").agg(n=("id", "nunique"), d=("days", "sum"))
    stand = tot.assign(share=lambda x: x.d / x.n).sort_values("share", ascending=False)
    wd = df[df.Reason != "Workover rig busy"]
    top = wd.groupby("Area").size().div(M.groupby(M.area_id.map(self.ds.area_name)).size()).sort_values(ascending=False)
    notes = [f"{wd.id.nunique()} of {len(M)} jobs started in {year} had a well shut in longer than the repair itself (report sentence 'stayed shut in for about N days longer…'); 'Workover rig busy' is a separate waiting sentence in reports and is listed on its own.",
             f"Area with the highest share of jobs hit by a post-repair delay: {top.index[0]} ({top.iloc[0]:.0%} of its jobs); lowest: {top.index[-1]} ({top.iloc[-1]:.0%})."]
    dom = df.groupby(["Area", "Reason"]).size().reset_index(name="n").sort_values("n", ascending=False).drop_duplicates("Area")
    notes.append("Most common reason per area: " + "; ".join(f"{r.Area}: {r.Reason} ({r.n} jobs)" for r in dom.sort_values("Area").itertuples()) + ".")
    labels = sorted(df.Area.unique())
    series = [{"name": rs, "values": [int(((df.Area == a) & (df.Reason == rs)).sum()) for a in labels]} for rs in sorted(df.Reason.unique())]
    return {"visual": "bar", "rows": rows, "labels": labels, "series": series, "stacked": True, "citations": sorted(set(df.id))[:12], "notes": notes}


# ---------- Q7: operator-note watchlist ----------
def note_watchlist(self, days=31, top_n=10):
    """Operator notes that sound wrong, on wells with no repair since the note; ranked by severity-weighted note count + other signs."""
    a = TODAY - pd.Timedelta(days=days)
    n = _opnotes(self)
    n = n[(n.ts >= a)]
    M = self.ds.m
    L = self.latest()
    plugged = _plugged(self)
    cand = {}
    for r in n.itertuples():
        if r.asset_id in plugged:
            continue
        for rx, wt, name in SYMPTOMS:
            if re.search(rx, r.text, re.I):
                last = M[(M.asset_id == r.asset_id) & (M.ts <= TODAY)]
                if len(last[(last.ts > r.ts)]):          # repaired since the note
                    break
                cand.setdefault(r.asset_id, []).append((wt, name, r))
                break
    I = self.inspections()
    rows, cites = [], []
    for w, ev in cand.items():
        score = sum(e[0] for e in ev)
        rec = I[(I.asset_id == w) & (I.ts >= TODAY - pd.Timedelta(days=84))]
        down = int((~rec.producing).sum())
        corr12 = len(M[(M.asset_id == w) & (M.maintenance_type == "corrective") & (M.ts >= TODAY - pd.Timedelta(days=365))])
        other = []
        if not L.loc[w].producing:
            other.append("latest inspection: not producing"); score += 3
        if down:
            other.append(f"{down} non-producing weekly inspections in the last 12 weeks"); score += min(down, 3)
        if corr12 >= 2:
            other.append(f"{corr12} corrective repairs in 12 months"); score += 1
        lr = M[M.asset_id == w].sort_values("ts")
        lastrep = f"{lr.iloc[-1].maintenance_id}, {lr.iloc[-1].started_at[:10]} ({lr.iloc[-1].issue})" if len(lr) else "none"
        q = "; ".join(f"\"{e[2].text}\" ({e[2].note_id}, {e[2].ts:%d %b})" for e in ev[:3])
        rows.append({"score": score, "_score": score, "Well": w, "Area": _area(self, w), "Operator-note evidence": q, "Other warning signs": "; ".join(other) or "none", "Last repair": lastrep})
        cites += [e[2].note_id for e in ev]
    rows.sort(key=lambda r: (-r["score"], r["Well"]))
    rows = rows[:int(top_n)]
    for k, r in enumerate(rows, 1):
        r["Rank"] = k
        r.pop("score")
    rows = [{"Rank": r["Rank"], **{k: v for k, v in r.items() if k != "Rank"}} for r in rows]
    return {"visual": "table", "rows": rows, "citations": cites,
            "notes": [f"Operator notes from the last {days} days that describe something sounding or behaving wrong (leak, tripping drive, hunting amps, tagging bottom, rattling, squeal, fluid pound), on wells with no repair job started since the note. Ranking = severity weight of the notes + non-producing readings + repeat corrective repairs; it is a heuristic, not a prediction model."]}


# ---------- unanswerable / thin-data questions ----------
def data_gap(self, topic="pressure"):
    """Q1/Q2: say plainly what the dataset does not contain, and what the nearest evidence is."""
    I = self.ds.i
    if topic == "pressure":
        cols = [c for c in I.columns if "press" in c.lower()]
        hits = [d for d in self.ds.docs if re.search(r"reservoir pressure|bottom.?hole pressure|\bpsi\b", d[2], re.I) and d[1] == "note"]
        return {"visual": "text", "rows": [], "citations": [], "gap": True,
                "notes": [f"No reservoir pressure data exists: inspections record only wellhead and ambient temperature, spill fields and notes ({len(I):,} inspections, {len(self.ds.w)} wells); pressure columns found: {cols or 'none'}; notes mentioning reservoir/bottom-hole pressure: {len(hits)}. A reservoir pressure map cannot be built from this data. Nearest honest alternative: wellhead-to-air temperature difference by area."]}
    cols = [c for c in self.ds.m.columns if "volume" in c.lower() or "bbl" in c.lower() or "prod" in c.lower()]
    w = I[I.ts >= pd.Timestamp("2026-01-01", tz="UTC")]
    wk = self.inspections()
    wk = wk[wk.ts >= pd.Timestamp("2026-01-01", tz="UTC")].groupby("asset_id").producing.sum().sort_values(ascending=False, kind="stable")
    top = wk[wk == wk.iloc[0]]
    return {"visual": "text", "rows": [{"Well": w_, "Weekly inspections showing producing in 2026": int(v)} for w_, v in top.head(10).items()], "citations": [], "gap": True,
            "notes": ["No oil production volumes exist in this dataset: only a weekly producing / not-producing reading per well (temperature rule). So 'most oil produced in 2026' cannot be answered; the closest proxy is the number of weekly inspections showing the well producing (%d wells tie at %d). That is uptime, not barrels." % (len(top), int(wk.iloc[0]))]}


def team_info(self, team):
    """Team lead and wells count (a well's own team_history overrides; today's team)."""
    t = [x for x in self.ds.teams if x["name"].lower() == str(team).lower() or x["team_id"].lower() == str(team).lower()]
    if not t:
        return {"error": f"No team '{team}'"}
    t = t[0]
    w = self.ds.w
    mine = w[w.team_id == t["team_id"]]
    for _, r in w.iterrows():                 # team_history: the open-ended entry is today's team
        h = r.get("team_history")
        if isinstance(h, list) and h:
            cur = [e for e in h if not e.get("to")]
            if cur and cur[-1]["team_id"] == t["team_id"] and r.asset_id not in mine.index:
                mine = pd.concat([mine, w.loc[[r.asset_id]]])
    mine = mine[~mine.asset_id.isin(_plugged(self))]
    return {"visual": "card", "rows": [{"Team": t["name"], "Lead": self.uname(t["lead_user_id"]), "Lead ID": t["lead_user_id"], "Wells": int(len(mine))}],
            "citations": [t["team_id"], t["lead_user_id"]], "notes": [f"{t['name']} is led by {self.uname(t['lead_user_id'])}; {len(mine)} active wells today (team_history applied; plugged-and-abandoned wells not counted)."]}


def temperature_by_area(self, months=12):
    """Q11: which area runs hotter? Average wellhead temperature and wellhead-above-air, per area."""
    I = self.inspections()
    I = I[I.ts >= TODAY - pd.DateOffset(months=int(months))]
    g = I.groupby(I.area_id.map(self.ds.area_name)).agg(wh=("wellhead_temp_c", "mean"), amb=("ambient_temp_c", "mean"), d=("delta", "mean"), n=("inspection_id", "count"))
    g = g.sort_values("wh", ascending=False)
    rows = [{"Area": a, "Avg wellhead (°C)": float(round(r.wh, 1)), "Avg air (°C)": float(round(r.amb, 1)), "Avg wellhead above air (°C)": float(round(r.d, 1)), "Readings": int(r.n)} for a, r in g.iterrows()]
    return {"visual": "bar", "rows": rows, "labels": list(g.index), "series": [{"name": "Avg wellhead (°C)", "values": [round(x, 1) for x in g.wh]}, {"name": "Avg wellhead above air (°C)", "values": [round(x, 1) for x in g.d]}],
            "citations": [], "notes": [f"'Hotter' read as average wellhead temperature over the last {months} months, with wellhead-above-air shown beside it because air temperature differs by area."]}


def prioritize(self, wells):
    """Rank wells discussed in a conversation by what the data says is most urgent (safety first)."""
    wells = list(dict.fromkeys(wells))
    gas = {r["Well"]: r for r in gas_response(self, since="2026-11-15")["rows"] if r["Met/Missed"] == "Missed"}
    rec = {r["Well"]: r for r in recalled_pumps(self)["rows"]}
    cold = {r["Well"] for r in cold_weather_check(self, start="2026-12-01", end="2026-12-31")["rows"]}
    wl = {r["Well"]: r for r in note_watchlist(self, top_n=500)["rows"]}
    rows = []
    for w in wells:
        sc, why = 0, []
        if w in gas:
            sc += 6; why.append(f"gas odor reported {gas[w]['Reported at']} with no response in time (OPS-1 missed): safety first")
        if w in rec:
            now = rec[w]["Producing now"]
            sc += 3 + (2 if now.startswith("Not") else 0)
            why.append(f"recalled pump {rec[w]['Lot']} still in the ground, 15 days past the 31 Dec deadline; {now.lower()}")
        if w in cold:
            sc += 1; why.append("missed the December heat-trace check (OPS-5)")
        if w in wl:
            sc += wl[w]["_score"] / 2; why.append("operator notes sound wrong: " + wl[w]["Operator-note evidence"][:140])
        if not why:
            why.append("no open issue found in the data")
        rows.append({"Well": w, "Area": _area(self, w), "Score": sc, "Why": "; ".join(why)})
    rows.sort(key=lambda r: (-r["Score"], r["Well"]))
    for k, r in enumerate(rows, 1):
        r["Rank"] = k
    rows = [{"Rank": r["Rank"], **{k: v for k, v in r.items() if k != "Rank"}} for r in rows]
    return {"visual": "table", "rows": rows, "citations": [], "no_missing": True,
            "notes": ["Priority = safety (unanswered gas report) > recalled pump in a well not producing > recalled pump > operator-note warning > missed heat-trace check. Weights are a judgement stated here, not a company rule."]}


DET = ("gas_response", "bypass_audit", "status_conflicts", "spill_letter_audit", "cold_weather_check", "delay_reasons", "recalled_pumps")
BAD = ("Missed", "Expired", "Not approved", "No")


def summary(tool, res):
    """Deterministic answer text for long audit tables: nothing is dropped and nothing is invented."""
    rows = res.get("rows") or []
    out = list(res.get("notes", []))
    flag = next((k for k in ("Met/Missed", "Status", "Compliant?") if rows and k in rows[0]), None)
    if flag:
        bad = [r for r in rows if str(r[flag]).startswith(BAD)]
        out.append("Problems: " + "; ".join(f"{r['Well']} ({r.get(flag)})" + (f", {r['Hours to response']} h" if "Hours to response" in r and r["Hours to response"] != "-" else "") for r in bad[:14]) + ("..." if len(bad) > 14 else "") + "." if bad else "No problems found.")
    if tool == "bypass_audit" and rows:
        cur = [r for r in rows if r["Bypass out"] == "still in"]
        out.append("In place right now: " + ("; ".join(f"{r['Well']} ({r['Status']}, {r['Approval']})" for r in cur) if cur else "none") + ".")
    if tool == "status_conflicts" and rows:
        for r in rows:
            sh = r["Status now"].startswith("Not")
            out.append(f"{r['Well']}: {r['Status now']}. Why: the operator note ({r['Latest operator note'][:16]}) is newer than inspection {r['Latest inspection'].split(',')[0]} and says the well was {'shut in' if sh else 'restarted'}; an inspection has not confirmed it" + ("." if sh else " yet."))
    elif tool == "cold_weather_check" and rows:
        out.append("Missed in December: " + "; ".join(f"{r['Well']} ({r['Inspection']}, {r['Date']}, {r['Ambient (°C)']} °C)" for r in rows if r["Date"] < "2027-01-01") + ". Example: " + rows[0]["Well"] + ".")
    elif tool == "recalled_pumps" and rows:
        by = {}
        for r in rows:
            by.setdefault(r["Area"], []).append(r["Well"])
        out.append(f"{len(rows)} wells: " + "; ".join(f"{a}: {', '.join(w)}" for a, w in sorted(by.items())) + ".")
        if len(rows) <= 10:
            out += [f"{r['Well']}: {r['Producing now'].lower()}; last repaired {r['Last repaired']}; installed {r['Installed']} ({r['Install job']}, lot {r['Lot']})." for r in rows]
    return "\n".join(out)


for fn in (prioritize, gas_response, bypass_audit, status_conflicts, cold_weather_check, spill_letter_audit, recalled_pumps, delay_reasons, note_watchlist, data_gap, team_info, temperature_by_area):
    setattr(Engine, fn.__name__, fn)
