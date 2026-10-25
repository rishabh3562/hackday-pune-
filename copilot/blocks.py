"""Composes several visualization blocks for one answer, deterministically (no LLM). Both front ends render the same `blocks`.
Block types: kpis, callout, status, table, bar, line, donut, scatter, heatmap, map, timeline.
Each block: {"type", "title", ...payload, "span": "full"|"half"}."""
import pandas as pd

from .data import TODAY

NUM = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
HIDE = {"lat", "lon", "Inspections", "_score"}


# ---------- constructors ----------
def kpis(items, title=None): return {"type": "kpis", "title": title, "items": items, "span": "full"}
def code(text, title=None): return {"type": "code", "title": title, "text": text, "span": "full"}
def callout(tone, title, text=""): return {"type": "callout", "tone": tone, "title": title, "text": text, "span": "full"}
def status(card): return {"type": "status", "title": None, "card": card, "span": "full"}
def table(rows, title=None, hide=HIDE):
    if not rows: return None
    cols = [k for k in rows[0] if k not in hide]
    return {"type": "table", "title": title, "columns": cols, "rows": [{c: r.get(c) for c in cols} for r in rows[:200]], "span": "full"}
def bar(labels, series, title=None, unit=""): return {"type": "bar", "title": title, "labels": labels, "series": series, "unit": unit, "span": "half"}
def line(labels, series, title=None, flags=None, unit=""): return {"type": "line", "title": title, "labels": labels, "series": series, "flags": flags, "unit": unit, "span": "half"}
def donut(labels, values, title=None): return {"type": "donut", "title": title, "labels": labels, "values": values, "span": "half"}
def scatter(points, x, y, title=None): return {"type": "scatter", "title": title, "points": points, "xLabel": x, "yLabel": y, "span": "half"}
def heatmap(rows, cols, values, title=None): return {"type": "heatmap", "title": title, "rowLabels": rows, "cols": cols, "values": values, "span": "full"}
def mapb(pins, title=None): return {"type": "map", "title": title, "pins": pins, "span": "half"} if pins else None
def timeline(events, title=None): return {"type": "timeline", "title": title, "events": events, "span": "full"} if events else None


def _clean(blocks): return [b for b in blocks if b]


# ---------- generic helpers (also used for "show it as a ...") ----------
def _cols(rows):
    keys = [k for k in rows[0] if k not in HIDE]
    nums = [k for k in keys if NUM(rows[0][k])]
    label = next((k for k in keys if isinstance(rows[0][k], str) and k not in nums), keys[0])
    pref = next((k for k in nums if any(w in k.lower() for w in ("days", "cost", "bbl", "total", "spills", "repairs", "mean", "wells", "reports"))), nums[0] if nums else None)
    return label, nums, pref


def from_rows(rows, visual, title=None):
    """One chart/table block from generic rows; used for the fallback and for re-rendering a previous result."""
    if not rows: return None
    label, nums, pref = _cols(rows)
    if visual in ("bar", "line") and pref:
        series = [{"name": k, "values": [r[k] for r in rows]} for k in (nums if visual == "line" else [pref])]
        return (bar if visual == "bar" else line)([str(r[label]) for r in rows], series, title)
    if visual == "donut" and pref: return donut([str(r[label]) for r in rows], [r[pref] for r in rows], title)
    if visual == "map":
        return mapb([{"lat": r["lat"], "lon": r["lon"], "label": r.get("Well") or r.get("well") or "", "detail": str(r.get("Date", "")), "tone": "bad"} for r in rows if r.get("lat") is not None], title)
    return table(rows, title)


def rerender(res, visual):
    rows = res.get("rows") or []
    return _clean([from_rows(rows, visual), table(rows, "Data")] if visual != "table" else [table(rows)])


# ---------- per-tool compositions ----------
def _well_events(e, well):
    ds, ev = e.ds, []
    since = TODAY - pd.Timedelta(days=150)
    i = e.inspections(); i = i[(i.asset_id == well) & (i.ts >= since) & (i.ts <= TODAY + pd.Timedelta(days=1))]
    for r in i.itertuples():
        if not r.producing: ev.append({"date": str(r.ts.date()), "title": "Not producing", "detail": f"{r.inspection_id}: +{r.delta:.1f} °C vs limit {r.threshold:g}", "tone": "bad"})
        if r.spill_detected: ev.append({"date": str(r.ts.date()), "title": f"Spill {r.spill_est_volume_bbl} bbl", "detail": r.inspection_id, "tone": "warn"})
    for m in ds.m[(ds.m.asset_id == well) & (ds.m.ts >= since)].itertuples():
        ev.append({"date": str(m.ts.date()), "title": f"{m.maintenance_type.title()} repair", "detail": f"{m.maintenance_id}: {m.issue}", "tone": "info"})
    for g in ds.r[(ds.r.asset_id == well) & (ds.r.ts >= since)].itertuples():
        ev.append({"date": str(g.date), "title": g.event_type.replace("_", " "), "detail": f"{g.event_id} {g.status}" + (f", fine USD {int(g.fine_usd)}" if g.fine_usd else ""), "tone": "bad" if g.fine_usd else "info"})
    for n in ds.n[(ds.n.asset_id == well) & (ds.n.ts >= since)].itertuples():
        ev.append({"date": str(n.ts.date()), "title": n.note_type.replace("_", " "), "detail": f"{n.note_id}: {n.text[:120]}", "tone": "muted"})
    return sorted(ev, key=lambda x: x["date"], reverse=True)[:14]


def _status(e, res):
    c = res["rows"][0]; well = c["well"]
    ts = e.timeseries(well, 13)["rows"]
    out = [status(c)]
    if c.get("recorded_status_stale"): out.append(callout("warn", "Recorded status is out of date", f"The system says '{c['recorded_status']}', but the inspections show the well is {'producing' if c['producing'] else 'not producing'}."))
    if c.get("correction"): out.append(callout("info", "Corrected reading", f"{c['correction']} (original {c.get('original_wellhead_temp_c')} °C kept)."))
    for r in c.get("open_repairs", []): out.append(callout("warn", f"Open repair {r['id']}", f"{r['issue']} (since {r['started']}, planned end {r['planned_end']})."))
    for n in c.get("notes", []): out.append(callout("info", f"Note {n['id']} by {n['by']}", n["text"]))
    for f in c.get("shared_facts", []): out.append(callout("warn" if f["status"] == "unconfirmed" else "info", f"{f['by']} ({f['status']})", f["text"]))
    if ts:
        out.append(line([r["date"] for r in ts], [{"name": "Wellhead °C", "values": [r["wellhead_temp_c"] for r in ts]}, {"name": "Air °C", "values": [r["ambient_temp_c"] for r in ts]}],
                        "Last 13 weeks", flags=[bool(r["producing"]) for r in ts]))
        out.append(scatter([{"x": r["ambient_temp_c"], "y": r["wellhead_temp_c"], "label": r["date"], "flag": bool(r["producing"])} for r in ts], "Air °C", "Wellhead °C", "Wellhead vs air (green = producing)"))
    out.append(timeline(_well_events(e, well), "Recent events"))
    meta = e.ds.w.loc[well]
    out.append(mapb([{"lat": float(meta["lat"]), "lon": float(meta["lon"]), "label": well, "detail": c["area"], "tone": "ok" if c["producing"] else "bad"}], "Location"))
    return out


def _not_producing(e, res):
    rows = res["rows"]
    noreason = [r for r in rows if "No recorded reason" in r["Reason"]]
    stale = [r for r in rows if "out of date" in r["Recorded status"]]
    out = [kpis([{"label": "Not producing", "value": len(rows), "tone": "bad"}, {"label": "No recorded reason", "value": len(noreason), "tone": "warn" if noreason else "ok"},
                 {"label": "Out-of-date status", "value": len(stale), "tone": "warn" if stale else "ok"}]), table(rows, "Wells")]
    if noreason: out.append(callout("warn", f"{len(noreason)} wells have no recorded reason", "Suggest a field check: " + ", ".join(r["Well"] for r in noreason) + "."))
    if rows: out.append(bar([r["Well"] for r in rows], [{"name": "Wellhead above air (°C)", "values": [r["Wellhead above air (°C)"] for r in rows]}], "How close to ambient (°C)", "°C"))
    out.append(mapb([{"lat": float(e.ds.w.loc[r["Well"], "lat"]), "lon": float(e.ds.w.loc[r["Well"], "lon"]), "label": r["Well"], "detail": r["Reason"][:80], "tone": "bad"} for r in rows], "Where"))
    return out


def _downtime(e, res):
    rows = res["rows"]
    if not rows: return [table(rows)]
    by_type = pd.DataFrame(rows).groupby("Type")["Downtime (days)"].sum()
    return _clean([kpis([{"label": "Total downtime (days)", "value": sum(r["Downtime (days)"] for r in rows)}, {"label": "Wells", "value": len(rows)}, {"label": "Worst", "value": rows[0]["Well"]}]),
                   bar([r["Well"] for r in rows], [{"name": "Downtime (days)", "values": [r["Downtime (days)"] for r in rows]}], "Downtime by well", "days"),
                   donut(list(by_type.index), [int(v) for v in by_type.values], "Share by well type"), table(rows, "Detail")])


def _spills(e, res):
    rows = res["rows"]
    if not rows or "Date" not in rows[0]: return [table(rows)] if rows else []
    cls = pd.Series([r["Class"] for r in rows]).value_counts()
    bymonth = pd.Series([r["Date"][:7] for r in rows]).value_counts().sort_index()
    return _clean([kpis([{"label": "Spills", "value": res.get("count", len(rows))}, {"label": "Total barrels", "value": res.get("total_bbl", 0)},
                         {"label": "Reportable (5 bbl+)", "value": int(sum(1 for r in rows if r["Class"] in ("reportable", "major"))), "tone": "warn"}]),
                   table(rows, "Spills"), mapb([{"lat": r["lat"], "lon": r["lon"], "label": r["Well"], "detail": f"{r['Date']} {r['Barrels']} bbl", "tone": "bad"} for r in rows], "Where"),
                   donut(list(cls.index), [int(v) for v in cls.values], "By class"), bar(list(bymonth.index), [{"name": "Spills", "values": [int(v) for v in bymonth.values]}], "By month")])


def _heatmap(e, res):
    rows, months = res["rows"], res.get("months", [])
    tot = {m: sum(r[m] for r in rows) for m in months}
    peak = max(tot, key=tot.get) if tot else None
    return _clean([kpis([{"label": "Spills", "value": sum(r["Total"] for r in rows)}, {"label": "Peak month", "value": peak or "-"}, {"label": "Worst area", "value": max(rows, key=lambda r: r["Total"])["Area"] if rows else "-"}]),
                   heatmap([r["Area"] for r in rows], months, [[r[m] for m in months] for r in rows], "By area and month"),
                   bar([r["Area"] for r in rows], [{"name": "Spills", "values": [r["Total"] for r in rows]}], "Total by area"),
                   line(months, [{"name": "Spills", "values": [tot[m] for m in months]}], "Trend by month")])


def _timeseries(e, res):
    rows = res["rows"]; np_ = [r["date"] for r in rows if not r["producing"]]
    return _clean([kpis([{"label": "Readings", "value": len(rows)}, {"label": "Not producing", "value": len(np_), "tone": "bad" if np_ else "ok"}]),
                   line([r["date"] for r in rows], [{"name": "Wellhead °C", "values": [r["wellhead_temp_c"] for r in rows]}, {"name": "Air °C", "values": [r["ambient_temp_c"] for r in rows]}], "Wellhead vs air", flags=[bool(r["producing"]) for r in rows]),
                   callout("bad", "Not producing on " + ", ".join(np_), "The rise over air was below the type threshold.") if np_ else None,
                   scatter([{"x": r["ambient_temp_c"], "y": r["wellhead_temp_c"], "label": r["date"], "flag": bool(r["producing"])} for r in rows], "Air °C", "Wellhead °C"),
                   table(rows, "Readings", hide=HIDE | {"inspection"})])


def _compliance(e, res):
    rows, pend = res["rows"], res.get("pending", [])
    proto = pd.Series([r["Protocol"] for r in rows]).value_counts() if rows else pd.Series(dtype=int)
    return _clean([kpis([{"label": "Breaches", "value": len(rows), "tone": "bad" if rows else "ok"}, {"label": "Open actions", "value": len(pend), "tone": "warn" if pend else "ok"}]),
                   table(rows, "Breaches"), table(pend, "Open actions (not breaches yet)"),
                   donut(list(proto.index), [int(v) for v in proto.values], "Breaches by protocol") if len(proto) else None,
                   *[callout("info", n) for n in res.get("notes", [])[:2]]])


def _money(e, res):
    rows = res["rows"]
    if not rows: return []
    label, nums, pref = _cols(rows)
    top = sorted(rows, key=lambda r: -(r[pref] or 0))[:8]
    return _clean([kpis([{"label": pref, "value": sum((r[pref] or 0) for r in rows)}, {"label": "Rows", "value": len(rows)}]),
                   from_rows(rows[:25], "bar", pref), donut([str(r[label]) for r in top], [r[pref] for r in top], "Share, top 8"), table(rows, "Detail")])


def _cause(e, res):
    rows = res["rows"]
    if not rows: return _clean([*[callout("info", n) for n in res.get("notes", [])[:3]]])
    by_cause = pd.Series([r["Root cause (quote)"] for r in rows]).value_counts()
    return _clean([kpis([{"label": "Wells", "value": len(rows)}, {"label": "Reports", "value": sum(r["Reports"] for r in rows)}, {"label": "Repair cost (USD)", "value": sum(r["Repair cost (USD)"] for r in rows)}]),
                   bar([r["Well"] for r in rows[:12]], [{"name": "Reports", "values": [r["Reports"] for r in rows[:12]]}], "Most affected wells"),
                   donut([c[:42] for c in by_cause.index[:6]], [int(v) for v in by_cause.values[:6]], "Root-cause wording"), table(rows, "Wells"),
                   *[callout("info", n) for n in res.get("notes", [])[:2]]])


def _trace(e, res):
    rows = res["rows"]
    tone = {"inspection": "info", "maintenance": "info", "regulatory": "bad", "note": "muted", "fact": "warn", "report": "info", "well": "ok"}
    return _clean([timeline([{"date": r["Type"], "title": f"{r['Relation']}: {r['ID']}", "detail": r["Detail"], "tone": tone.get(r["Type"], "muted")} for r in rows], "Linked records"), table(rows, "Detail")])


def _sql(e, res):
    rows = res["rows"]
    return _clean([callout("warn", "Open-ended query (ad-hoc, less verified than the typed tools)", res.get("explain", "")), code(res["sql"], "SQL that was run (read-only, on the corrected data)"),
                   table(rows, f"{len(rows)} rows") if rows else callout("info", "No rows returned"),
                   from_rows(rows[:30], "bar") if rows and len(rows) > 1 and len(rows[0]) == 2 and NUM(list(rows[0].values())[1]) else None])


def _ops(e, res):
    """Operations-SOP tools: the table the question asked for, a chart when the tool made one, the notes as callouts."""
    rows = res.get("rows") or []
    chart = bar(res["labels"], res["series"], None) if res.get("labels") else None
    if chart and res.get("stacked"):
        chart["stacked"], chart["span"] = True, "full"
    flag = next((k for k in ("Met/Missed", "Status", "Compliant?") if rows and k in rows[0]), None)
    tone = {"kpi": None}
    kp = None
    if flag:
        vals = [str(r[flag]) for r in rows]
        bad = sum(v.startswith(("Missed", "Expired", "Not approved", "No")) for v in vals)
        kp = kpis([{"label": "Rows", "value": len(rows)}, {"label": "Problems", "value": bad}])
    return _clean([kp, table(rows, None), chart, *[callout("info", n) for n in res.get("notes", [])[:3]]])


_OPS = ("gas_response", "bypass_audit", "status_conflicts", "cold_weather_check", "spill_letter_audit", "recalled_pumps", "delay_reasons",
        "note_watchlist", "data_gap", "team_info", "temperature_by_area", "prioritize")
_BY_TOOL = {**{t: _ops for t in _OPS}, "sql_query": _sql, "well_status": _status, "wells_not_producing": _not_producing, "downtime": _downtime, "timeseries": _timeseries, "compliance": _compliance,
            "wells_by_cause": _cause, "trace": _trace, "repair_costs": _money, "repair_summary": _money, "top_repairs": _money, "fines": _money,
            "spill_repair_cost": _money, "downtime_cost": _money}


def build(e, tool, res):
    """Blocks for one tool result. Falls back to the primary visual plus a table."""
    try:
        if tool == "spills":
            return _heatmap(e, res) if res.get("visual") == "heatmap" else _spills(e, res)
        if tool in _BY_TOOL and (res.get("rows") or tool in ("wells_by_cause",) + _OPS):
            return _clean(_BY_TOOL[tool](e, res))
    except Exception:  # noqa: BLE001  (never let a decoration break an answer)
        pass
    rows = res.get("rows") or []
    prim = from_rows(rows, res.get("visual", "table"))
    return _clean([prim, table(rows, "Data") if prim and prim["type"] != "table" and len(rows) <= 40 else None, *[callout("info", n) for n in res.get("notes", [])[:2]]])
