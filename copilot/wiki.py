"""LLM wiki: a living page per well, per well type and for the whole fleet.
Facts block  = generated from the data/corrections log on every request (deterministic, cited by record ID, never stale).
Insights block = model-written bullets over the facts, each with sources; checked against the facts (unknown IDs/numbers dropped), cached on the
facts hash, flagged stale when the facts change. Corrections and rules taught by users therefore flow into every page at their scope."""
import hashlib
import json
import os
import re
import time

import pandas as pd

from . import blocks as B
from .causes import cause_table
from .data import ANCHOR, TODAY_ISO
from .tools import Engine

CACHE_DIR = os.environ.get("WIKI_DIR", ".cache/wiki")
ID_RE = re.compile(r"\b(?:WELL-\d{4}|INS-\d{4}-\d{4}|MNT-\d{4}-\d{3}|CTX-\d{4}-\d{3}|REG-\d{4}-\d{3})\b")
NUM_RE = re.compile(r"(?<![\w.-])\d[\d,]*\.\d+|(?<![\w.-])\d{3,}")


def _md_table(rows, cols=None):
    if not rows: return "_none_"
    cols = cols or list(rows[0])
    return "\n".join(["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] + ["| " + " | ".join(str(r.get(c, "")).replace("|", "/") for c in cols) + " |" for r in rows])


def _taught(e, well=None, wtype=None):
    """Everything users taught that applies at this scope (well, its type, or the whole fleet)."""
    out = []
    for f in e.mem.facts(include_inactive=True):
        sel = json.loads(f["selector"]) if f.get("selector") else {}
        hit = (well and (f.get("scope_id") == well or well in (sel.get("wells") or []) or (f.get("inspection_id") or "").startswith(f"INS-{well[-4:]}-"))) \
            or (wtype and (f.get("scope_id") == wtype or sel.get("well_type") == wtype)) or (not well and not wtype)
        if hit: out.append({"id": f"#{f['id']}", "kind": f["kind"], "by": f["author"], "status": f["status"], "what": (f.get("text") or f.get("corrected") or "")[:160], "field": f.get("field")})
    return out


# ---------- facts ----------
def well_facts(e: Engine, well):
    ds = e.ds
    if well not in ds.w.index: raise KeyError(well)
    meta, st = ds.w.loc[well], e.well_status(well)["rows"][0]
    a = ANCHOR - pd.DateOffset(months=12)
    i = e.inspections(); i = i[(i.asset_id == well) & (i.ts >= a)]
    m = ds.m[(ds.m.asset_id == well) & (ds.m.ts >= a)]
    sp = i[i.spill_detected]; comp = e.compliance(well=well, months=12)
    cz = cause_table(e); cz = cz[(cz.asset_id == well)]
    by_eq = m[m.maintenance_type == "corrective"].groupby("equipment_kind").size()
    top_cause = cz.groupby("root_cause").size().sort_values(ascending=False).head(4)
    return {
        "profile": {"well": well, "name": meta["name"], "type": meta["well_type"], "area": ds.area_name.get(meta["area_id"]), "team": meta["team_id"], "in_charge": e.uname(meta["in_charge_user_id"]),
                    "installed": meta["installed_on"], "equipment": [f"{x['kind']} ({x['model']})" for x in meta["equipment"]]},
        "now": {"producing": st["producing"], "rise_c": st["delta_c"], "limit_c": st["threshold_c"], "rule": st["threshold_source"], "last_inspection": st["inspection"], "inspected_at": st["inspected_at"],
                "inspected_by": st["inspected_by"], "recorded_status": st["recorded_status"], "recorded_status_stale": st["recorded_status_stale"], "open_repairs": st["open_repairs"],
                "notes": [f"{n['id']} ({n['by']}): {n['text']}" for n in st["notes"]], "correction": st.get("correction")},
        "last_12_months": {"inspections": int(len(i)), "not_producing_inspections": int((~i.producing).sum()), "downtime_days": int((~i.producing).sum()) * 7, "spills": int(len(sp)), "spill_bbl": round(float(sp.spill_est_volume_bbl.sum()), 1),
                           "reportable_spills": int((sp.spill_est_volume_bbl >= ds.rules["reportable_bbl"]).sum()), "repairs": int(len(m)), "corrective_repairs": int((m.maintenance_type == "corrective").sum()),
                           "repair_cost_usd": int(m.cost_total.sum()), "corrective_by_equipment": {k: int(v) for k, v in by_eq.items()}},
        "compliance": {"breaches": comp["rows"], "open_actions": comp.get("pending", []), "notes": comp.get("notes", [])},
        "root_causes": [{"cause": c, "reports": int(n)} for c, n in top_cause.items()],
        "taught": _taught(e, well=well, wtype=meta["well_type"]),
        "recent_events": B._well_events(e, well)[:8],
    }


def type_facts(e: Engine, wtype):
    ds = e.ds; ids = list(ds.w[ds.w.well_type == wtype].asset_id)
    if not ids: raise KeyError(wtype)
    L = e.latest(ids); a = ANCHOR - pd.DateOffset(months=12)
    m = ds.m[ds.m.asset_id.isin(ids) & (ds.m.ts >= a)]; cor = m[m.maintenance_type == "corrective"].sort_values("ts").copy()
    cor["gap"] = cor.groupby("asset_id").ts.diff().dt.days
    cz = cause_table(e); cz = cz[cz.asset_id.isin(ids)]
    return {"profile": {"type": wtype, "wells": len(ids), "producing_now": int(L.producing.sum()), "limit_c": ds.rules["producing_delta"].get(wtype), "rule": ds.rules["prov"].get(f"producing_delta:{wtype}"),
                        "rca_threshold": ds.rules["rca_count"].get(wtype)},
            "last_12_months": {"repairs": int(len(m)), "corrective": int(len(cor)), "repair_cost_usd": int(m.cost_total.sum()), "mean_days_between_corrective": round(float(cor.gap.mean()), 1) if cor.gap.notna().any() else None},
            "top_root_causes": [{"cause": c, "reports": int(n)} for c, n in cz.groupby("root_cause").size().sort_values(ascending=False).head(6).items()],
            "wells_most_corrective": [{"well": w, "corrective": int(n)} for w, n in cor.groupby("asset_id").size().sort_values(ascending=False).head(8).items()],
            "taught": _taught(e, wtype=wtype)}


def fleet_facts(e: Engine):
    ds = e.ds; L = e.latest()
    comp = e.compliance(months=12)
    proto = pd.Series([r["Protocol"] for r in comp["rows"]]).value_counts().to_dict() if comp["rows"] else {}
    cz = cause_table(e)
    return {"kpis": {"wells": int(len(L)), "producing": int(L.producing.sum()), "not_producing": int((~L.producing).sum()), "stale_status": len(e.stale_status()["rows"]),
                     "open_fines_usd": int(sum(r["Fine (USD)"] for r in e.fines("open")["rows"])), "open_repairs": len(e.open_repairs_all()["rows"])},
            "areas": [{"area": a["name"], "wells": int((ds.w.area_id == a["area_id"]).sum()), "not_producing": int((~L[L.area_id == a["area_id"]].producing).sum())} for a in ds.areas],
            "obligations": {"breaches_by_protocol_12mo": proto, "open_actions": len(comp.get("pending", []))},
            "rules_in_force": [{"rule": k, "value": v, "source": ds.rules["prov"].get(k, "")} for k, v in ds.rules.items() if isinstance(v, float)] +
                              [{"rule": f"producing_delta {k}", "value": v, "source": ds.rules["prov"].get(f"producing_delta:{k}", "")} for k, v in ds.rules["producing_delta"].items()],
            "taught": _taught(e), "top_root_causes": [{"cause": c, "reports": int(n)} for c, n in cz.groupby("root_cause").size().sort_values(ascending=False).head(6).items()],
            "newly_stopped": [r["Well"] for r in e.newly_stopped()["rows"]]}


# ---------- rendering the facts as sections ----------
def _sections(kind, f):
    S = lambda id_, title, md: {"id": id_, "title": title, "kind": "facts", "md": md}
    if kind == "well":
        p, n, y = f["profile"], f["now"], f["last_12_months"]
        out = [S("profile", "Profile", f"**{p['well']}** is a **{p['type']}** well in **{p['area']}** ({p['team']}), in charge: {p['in_charge']}, installed {p['installed']}.\n\nEquipment: " + ", ".join(p["equipment"]) + "."),
               S("now", "Right now", f"- {'**Producing**' if n['producing'] else '**Not producing**'}: wellhead {n['rise_c']} °C above air, limit {n['limit_c']} °C ({n['rule']}).\n- Last inspection {n['last_inspection']} on {n['inspected_at']} by {n['inspected_by']}.\n"
                                       f"- Recorded status **{n['recorded_status']}**" + (" (out of date)." if n["recorded_status_stale"] else ".") +
                                       ("".join(f"\n- Open repair {r['id']}: {r['issue']} (planned end {r['planned_end']})." for r in n["open_repairs"])) + ("".join(f"\n- Note {x}" for x in n["notes"])) +
                                       (f"\n- Correction applied: {n['correction']}" if n["correction"] else "")),
               S("year", "Last 12 months", f"- {y['inspections']} inspections, {y['not_producing_inspections']} not producing = **{y['downtime_days']} days** of downtime.\n- {y['spills']} spills, {y['spill_bbl']} bbl, {y['reportable_spills']} reportable.\n"
                                           f"- {y['repairs']} repairs ({y['corrective_repairs']} corrective), USD {y['repair_cost_usd']:,}. Corrective by equipment: " + (", ".join(f"{k} {v}" for k, v in y["corrective_by_equipment"].items()) or "none") + ".")]
        c = f["compliance"]
        out.append(S("compliance", "Compliance", ("**Breaches**\n\n" + _md_table(c["breaches"], ["Protocol", "Spill", "Date", "Finding", "Evidence"]) if c["breaches"] else "No breaches in the last 12 months.") +
                     ("\n\n**Open actions**\n\n" + _md_table(c["open_actions"], ["Protocol", "Finding", "Evidence"]) if c["open_actions"] else "")))
        if f["root_causes"]: out.append(S("causes", "Recurring root causes", "\n".join(f"- {x['cause']} ({x['reports']} reports)" for x in f["root_causes"])))
        out.append(S("taught", "What the team taught me here", "\n".join(f"- {x['id']} {x['kind']} by {x['by']} [{x['status']}]: {x['what']}" for x in f["taught"]) or "Nothing yet."))
        out.append(S("events", "Recent events", "\n".join(f"- {x['date']}: **{x['title']}**, {x['detail']}" for x in f["recent_events"]) or "None."))
        return out
    if kind == "type":
        p, y = f["profile"], f["last_12_months"]
        return [S("profile", "Rules and fleet", f"**{p['type']}**: {p['wells']} wells, {p['producing_now']} producing. Producing when wellhead is at least **{p['limit_c']} °C** above air ({p['rule']}); root-cause analysis after **{p['rca_threshold']}** corrective repairs on the same equipment."),
                S("year", "Last 12 months", f"- {y['repairs']} repairs ({y['corrective']} corrective), USD {y['repair_cost_usd']:,}.\n- Mean days between corrective repairs: {y['mean_days_between_corrective']}."),
                S("causes", "Top root causes", "\n".join(f"- {x['cause']} ({x['reports']} reports)" for x in f["top_root_causes"])),
                S("wells", "Wells with most corrective repairs", _md_table([{"Well": x["well"], "Corrective (12 mo)": x["corrective"]} for x in f["wells_most_corrective"]])),
                S("taught", "Rules and feedback taught for this type", "\n".join(f"- {x['id']} {x['kind']} by {x['by']} [{x['status']}]: {x['what']}" for x in f["taught"]) or "Nothing yet.")]
    k, o = f["kpis"], f["obligations"]
    return [S("kpis", "Fleet today", f"{k['wells']} wells: **{k['producing']} producing**, **{k['not_producing']} not**; {k['stale_status']} stale recorded statuses; {k['open_repairs']} repairs in progress; open fines **USD {k['open_fines_usd']:,}**."),
            S("areas", "Areas", _md_table([{"Area": a["area"], "Wells": a["wells"], "Not producing": a["not_producing"]} for a in f["areas"]])),
            S("obligations", "Obligations (last 12 months)", f"Breaches by protocol: {', '.join(f'{k} ×{v}' for k, v in o['breaches_by_protocol_12mo'].items()) or 'none'}. Open actions: {o['open_actions']}. Newly stopped wells: {', '.join(f['newly_stopped']) or 'none'}."),
            S("taught", "Central corrections, rules and notes", "\n".join(f"- {x['id']} {x['kind']} by {x['by']} [{x['status']}]: {x['what']}" for x in f["taught"]) or "Nothing taught yet."),
            S("rules", "Rules in force (with source)", _md_table([{"Rule": r["rule"], "Value": r["value"], "Source": r["source"]} for r in f["rules_in_force"]])),
            S("causes", "Fleet-wide root causes", "\n".join(f"- {x['cause']} ({x['reports']} reports)" for x in f["top_root_causes"]))]


# ---------- insights (model-written, checked, cached) ----------
def _hash(f): return hashlib.md5(json.dumps(f, sort_keys=True, default=str).encode()).hexdigest()[:12]
def _path(kind, id_): return os.path.join(CACHE_DIR, f"{kind}-{id_}.json")


def _cached(kind, id_):
    try:
        with open(_path(kind, id_)) as fh: return json.load(fh)
    except (OSError, ValueError): return None


def generate_insights(kind, id_, facts):
    from .agent import call_llm, parse_json
    blob = json.dumps(facts, default=str)
    prompt = ("You write the insight section of an oil-field wiki page. Using ONLY the JSON facts, return JSON "
              '{"insights":[{"text":"<one specific, useful sentence>","sources":["<record IDs from the facts>"]}],"suggested_checks":["<a concrete follow-up an operator could do>"]}. '
              "3-5 insights: patterns, risks, contradictions between records, what is overdue. Cite record IDs (WELL-/INS-/MNT-/CTX-/REG-) that appear in the facts; "
              "never invent IDs or numbers; if the facts are thin, say less.")
    out = parse_json(call_llm([{"role": "system", "content": prompt}, {"role": "user", "content": blob[:9000]}], 900, json_mode=True))
    keep = []
    for it in out.get("insights", []):
        t = it.get("text", ""); ok = all(i in blob for i in ID_RE.findall(t)) and all(n.replace(",", "") in blob.replace(",", "") for n in NUM_RE.findall(t))
        if ok and t: keep.append({"text": t, "sources": [s for s in it.get("sources", []) if s in blob][:6]})
    page = {"insights": keep, "dropped": len(out.get("insights", [])) - len(keep), "suggested_checks": [c for c in out.get("suggested_checks", []) if all(i in blob for i in ID_RE.findall(c))][:4],
            "facts_hash": _hash(facts), "generated_at": time.strftime("%Y-%m-%d %H:%M"), "model": os.environ.get("VERTEX_MODEL", "gemini-2.5-flash")}
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(_path(kind, id_), "w") as fh: json.dump(page, fh)
    return page


def page(e: Engine, kind, id_):
    facts = {"well": well_facts, "type": type_facts}.get(kind, lambda e_, _i: fleet_facts(e_))(e, id_) if kind != "fleet" else fleet_facts(e)
    ins = _cached(kind, id_)
    title = {"well": f"{id_} · {e.ds.w.loc[id_, 'name']}" if kind == "well" else "", "type": f"Well type {id_}", "fleet": "Fleet wiki (central knowledge base)"}[kind]
    return {"kind": kind, "id": id_, "title": title, "as_of": TODAY_ISO, "facts_hash": _hash(facts), "sections": _sections(kind, facts), "facts": facts,
            "insights": ins, "insights_stale": bool(ins and ins["facts_hash"] != _hash(facts))}


def index(e: Engine):
    L = e.latest(); taught = e.mem.facts(); touched = {f["scope_id"] for f in taught if f.get("scope_id")} | {w for f in taught for w in (json.loads(f["selector"]).get("wells", []) if f.get("selector") else [])}
    return {"fleet": {"cached": os.path.exists(_path("fleet", "all"))},
            "types": [{"id": t, "wells": int((e.ds.w.well_type == t).sum()), "cached": os.path.exists(_path("type", t))} for t in sorted(e.ds.w.well_type.unique())],
            "wells": [{"id": w, "name": e.ds.w.loc[w, "name"], "type": e.ds.w.loc[w, "well_type"], "area": e.ds.area_name.get(e.ds.w.loc[w, "area_id"]), "producing": bool(L.loc[w, "producing"]) if w in L.index else None,
                       "taught": w in touched, "cached": os.path.exists(_path("well", w))} for w in e.ds.w.index]}
