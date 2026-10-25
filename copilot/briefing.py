"""Dashboard data: one deterministic call over the same tools the copilot uses (no LLM)."""
from .data import TODAY_ISO
from . import blocks as B
from .tools import Engine


def briefing(e: Engine, user_id=None):
    ds = e.ds
    latest = e.latest()
    total, producing = len(latest), int(latest.producing.sum())
    not_prod = e.wells_not_producing()["rows"]
    stale = e.stale_status()["rows"]
    newly = e.newly_stopped()["rows"]
    down14 = e.consecutive_down(14)["rows"]
    fines = e.fines("open")
    resp = e.spill_response_summary(12)
    open_rep = e.open_repairs_all()["rows"]
    s90 = e.spills(days=90)
    areas = []
    for a in ds.areas:
        ids = [w for w in latest.index if ds.w.loc[w, "area_id"] == a["area_id"]]
        sub = latest.loc[ids]
        areas.append({"area": a["name"], "wells": len(ids), "producing": int(sub.producing.sum()), "stopped": int((~sub.producing).sum()),
                      "stale": sum(1 for r in stale if r["Well"] in ids)})
    pins = [{"well": r["Well"], "lat": float(ds.w.loc[r["Well"], "lat"]), "lon": float(ds.w.loc[r["Well"], "lon"]),
             "note": r["Reason"][:90]} for r in not_prod]
    fine_total = sum(r["Fine (USD)"] for r in fines["rows"])
    late = resp.get("late_or_missing", 0)
    attention = [x for x in (
        {"level": "high", "title": f"{len(down14)} wells down more than 14 days", "detail": "RC-03: report to the area supervisor", "ask": "Which wells have been down for more than 14 consecutive days right now and must be reported to the supervisor (RC-03)?"} if down14 else None,
        {"level": "high", "title": f"{late} reportable spills reported late or never", "detail": "SR-01 breaches in the last 12 months", "ask": "Of the reportable spills in the last 12 months, how many were reported late or never, and what fines are still open?"} if late else None,
        {"level": "med", "title": f"{len(newly)} wells just stopped producing", "detail": "producing at the previous inspection, not at the latest", "ask": "Which wells stopped producing at their latest inspection after producing at the one before?"} if newly else None,
        {"level": "med", "title": f"USD {fine_total:,} in open fines", "detail": f"{len(fines['rows'])} notices of violation", "ask": "What is the total of open regulator fines across the field and which wells carry them?"} if fine_total else None,
        {"level": "low", "title": f"{len(stale)} wells with an out-of-date recorded status", "detail": "inspections disagree with the system of record", "ask": "Which wells have a recorded status that disagrees with their latest inspection?"} if stale else None,
        {"level": "low", "title": f"{len(open_rep)} repairs in progress", "detail": "planned end after today", "ask": "Which repairs are currently in progress across the field?"} if open_rep else None) if x]
    return {
        "today": TODAY_ISO,
        "kpis": [{"label": "Wells", "value": total}, {"label": "Producing now", "value": producing, "tone": "ok"},
                 {"label": "Not producing", "value": total - producing, "tone": "bad"}, {"label": "Stale status", "value": len(stale), "tone": "warn"},
                 {"label": "Spills, 90 days", "value": s90.get("count", 0)}, {"label": "Open fines (USD)", "value": fine_total, "tone": "warn" if fine_total else "ok"}],
        "attention": attention, "areas": areas,
        "downtime": B.from_rows(e.downtime(months=4, top_n=6)["rows"], "bar"),
        "stopped": B.mapb([{"lat": p["lat"], "lon": p["lon"], "label": p["well"], "detail": p["note"], "tone": "bad"} for p in pins]),
        "heatmap": (lambda r: B.heatmap([x["Area"] for x in r["rows"]], r["months"], [[x[m] for m in r["months"]] for x in r["rows"]]))(e.spills(year=int(TODAY_ISO[:4]), group_by="area_month")),
    }
