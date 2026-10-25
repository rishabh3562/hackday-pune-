"""Concept -> wells. 'Which wells are failing due to mud?'
Ingest lifts each report's Root cause section into a column (about 25 distinct phrasings in the sample). At query time:
 1. shortlist distinct root-cause phrases with hybrid retrieval (lexical overlap + embeddings; skipped when there are few phrases),
 2. one small LLM call judges which phrases are exact/related to the concept (JSON), with a reason,
 3. SQL-style aggregation over the structured column gives wells, counts, cost and dates,
 4. every row carries a verbatim quote from the report; if the literal term never occurs the answer says so and shows the closest causes."""
import re

import pandas as pd

from .tools import Engine


def _root_cause(text):
    m = re.search(r"## Root cause\s*\n+(.+?)(?:\n\s*\n|\n## |\Z)", text, re.S)
    if not m:
        return None
    return re.sub(r"\s+", " ", m.group(1)).strip()


def _norm(p):
    return re.sub(r"\d+(?:\.\d+)?", "N", p.lower()).strip(" .")


def cause_table(self):
    if getattr(self, "_causes", None) is None:
        rows = []
        for m in self.ds.m.itertuples():
            t = self.ds.reports.get(m.maintenance_id)
            rc = _root_cause(t) if t else None
            if rc:
                first = re.split(r"(?<=[.!?])\s", rc)[0]
                rows.append({"maintenance_id": m.maintenance_id, "asset_id": m.asset_id, "ts": m.ts, "cost": m.cost_total,
                             "equipment": m.equipment_kind, "root_cause": first, "key": _norm(first), "area_id": m.area_id})
        self._causes = pd.DataFrame(rows)
    return self._causes


def _judge(concept, phrases):
    from .agent import call_llm, parse_json
    listing = "\n".join(f"{i}: {p}" for i, p in enumerate(phrases))
    prompt = ("You map an operator's concept to root-cause statements from oil-well repair reports. Return JSON "
              '{"concept_meaning":"<what the concept means in well operations, one line>","matches":[{"i":<index>,"relation":"exact|related","why":"<short>"}]}. '
              "exact = the statement itself names the concept; related = the physical cause is of the same kind (same material or mechanism). "
              "Include nothing unrelated in matches. If nothing relates, return an empty matches list. Always add up to 3 nearest statements "
              "(closest physical kind, even if not the same) in nearest.")
    return parse_json(call_llm([{"role": "system", "content": prompt},
                                {"role": "user", "content": f"Concept: {concept}\nStatements:\n{listing}"}], 900, json_mode=True))


def wells_by_cause(self, concept, area=None, months=None, year=None, equipment=None, min_reports=1, top_n=None):
    ct = cause_table(self)
    if ct.empty:
        return {"visual": "text", "rows": [], "citations": [], "notes": ["No report in the data has a root-cause section."]}
    a, b = self.period(months=months, year=year)
    d = ct[(ct.ts >= a) & (ct.ts <= b)]
    if area:
        d = d[d.area_id == self.resolve_area(area)]
    if equipment:
        d = d[d.equipment == equipment]
    phrases = list(ct.groupby("key").root_cause.first().items())          # (key, example wording)
    terms = [t for t in re.findall(r"[a-z]{3,}", concept.lower())]
    literal = [k for k, p in phrases if any(t in p.lower() for t in terms)]
    short = phrases
    if len(phrases) > 40:                                                  # scale path: shortlist lexical + embedding neighbours
        short = [x for x in phrases if x[0] in literal]
        try:
            import numpy as np
            from .search import _embed
            v = np.array(_embed([p for _, p in phrases], "RETRIEVAL_DOCUMENT")); q = np.array(_embed([concept], "RETRIEVAL_QUERY")[0])
            sims = v @ q / (np.linalg.norm(v, axis=1) * np.linalg.norm(q))
            short += [phrases[i] for i in np.argsort(-sims)[:30] if phrases[i] not in short]
        except Exception:  # noqa: BLE001
            short = short or phrases[:40]
    verdict = _judge(concept, [p for _, p in short])
    chosen = {short[m["i"]][0]: m for m in verdict.get("matches", []) if isinstance(m.get("i"), int) and m["i"] < len(short)}
    notes = [f"Interpretation: {verdict.get('concept_meaning', concept)}"]
    if not literal:
        notes.append(f"No record uses the word '{concept}' literally; showing causes of the same kind.")
    if not chosen:
        notes.append(f"No root cause in the data matches '{concept}'.")
        sug = []
        for m in verdict.get("nearest", [])[:3]:
            if isinstance(m.get("i"), int) and m["i"] < len(short):
                k = short[m["i"]][0]
                dd = d[d.key == k]
                if len(dd):
                    sug.append({"cause": short[m["i"]][1].rstrip("."), "reports": int(len(dd)), "wells": int(dd.asset_id.nunique()), "why": m.get("why", "")})
        return {"visual": "text", "rows": [], "citations": [], "notes": notes, "suggestions": sug, "concept": concept,
                "window": ("all history" if a.year < 1990 else f"{a.date()} to {b.date()}")}
    hit = d[d.key.isin(chosen)]
    rows, cites = [], []
    for w, g in hit.groupby("asset_id"):
        if len(g) < int(min_reports):
            continue
        g = g.sort_values("ts")
        last = g.iloc[-1]
        rows.append({"Well": w, "Reports": int(len(g)), "Repair cost (USD)": int(g.cost.sum()), "Last": str(last.ts.date()),
                     "Match": chosen[last.key]["relation"], "Root cause (quote)": last.root_cause, "Repairs": ", ".join(g.maintenance_id)})
        cites += list(g.maintenance_id)
    rows.sort(key=lambda r: (-r["Reports"], r["Well"]))
    if top_n:
        rows = rows[: int(top_n)]
    summ = hit.groupby("key").size().sort_values(ascending=False)
    for k, n in summ.items():
        notes.append(f"{chosen[k]['relation']}: \"{ct[ct.key == k].root_cause.iloc[0]}\" ({n} reports) - {chosen[k].get('why', '')}")
    out = {"visual": "table", "rows": rows, "citations": cites[:80], "notes": notes[:8]}
    if not literal and not any(m.get("relation") == "exact" for m in chosen.values()):
        # the word never occurs: related causes are offered back to the user as grounded options, not silently listed
        out["suggestions"] = [{"cause": ct[ct.key == k].root_cause.iloc[0].rstrip("."), "reports": int(n), "wells": int(hit[hit.key == k].asset_id.nunique()),
                               "why": chosen[k].get("why", "")} for k, n in summ.items()][:4]
        out["concept"], out["window"] = concept, ("all history" if a.year < 1990 else f"{a.date()} to {b.date()}")
    return out


def trace(self, entity_id):
    """Everything linked to an inspection / repair / well / event (the graph, walked over ID links; no graph DB needed)."""
    ds, e = self.ds, entity_id.strip()
    rows, cites = [], [e]
    def add(rel, kind, id_, detail):
        rows.append({"Relation": rel, "Type": kind, "ID": id_, "Detail": detail}); cites.append(id_)
    ins = set()
    if e.startswith("INS-"):
        ins.add(e)
    if e.startswith("MNT-"):
        m = ds.m[ds.m.maintenance_id == e]
        for r in m.itertuples():
            add("this repair", "maintenance", e, f"{r.issue} ({r.maintenance_type}, {r.equipment_kind}, USD {int(r.cost_total)})")
            if isinstance(r.triggered_by_inspection_id, str):
                ins.add(r.triggered_by_inspection_id)
            if e in ds.reports:
                add("has report", "report", e, (_root_cause(ds.reports[e]) or "")[:150])
    for iid in ins:
        r = ds.i[ds.i.inspection_id == iid]
        for x in r.itertuples():
            add("inspection", "inspection", iid, f"{x.asset_id} {x.ts.date()} spill={x.spill_detected} vol={x.spill_est_volume_bbl}")
        for m in ds.m[ds.m.triggered_by_inspection_id == iid].itertuples():
            add("triggered repair", "maintenance", m.maintenance_id, f"{m.issue}, USD {int(m.cost_total)}, contained {m.contain_hours}h" if pd.notna(m.contain_hours) else f"{m.issue}, USD {int(m.cost_total)}")
        for g in ds.r[ds.r.related_inspection_id == iid].itertuples():
            add("regulator event", "regulatory", g.event_id, f"{g.event_type} {g.date} fine {int(g.fine_usd)} {g.status}")
        for n in ds.n[(ds.n.inspection_id == iid) | ds.n.text.str.contains(iid, regex=False)].itertuples():
            add("note", "note", n.note_id, n.text[:150])
    for f in self.mem.facts(include_inactive=True):
        if f.get("inspection_id") in ins:
            add("correction", "fact", f"#{f['id']}", f"{f['author']}: {f['field']} {f['original']} -> {f['corrected']} [{f['status']}]")
    if e.startswith("WELL-") and e in ds.w.index:
        w = ds.w.loc[e]
        add("well", "well", e, f"{w['well_type']} {self.ds.area_name.get(w['area_id'])}, recorded {w['recorded_status']}")
        add("recent repairs", "maintenance", e, f"{int((ds.m.asset_id == e).sum())} total, {int(((ds.m.asset_id == e) & (ds.m.maintenance_type == 'corrective')).sum())} corrective")
        add("regulator events", "regulatory", e, f"{int((ds.r.asset_id == e).sum())} events, open fines USD {int(ds.r[(ds.r.asset_id == e) & (ds.r.status == 'open')].fine_usd.sum())}")
    return {"visual": "table", "rows": rows, "citations": cites[:60], "notes": [f"Linked records for {e}, walked over ID references."]}


def root_causes(self, well, equipment=None, months=None, year=None):
    """Why did THIS well's repairs happen: the root-cause text of each repair report, newest first (deterministic, quoted from the reports)."""
    ct = cause_table(self)
    d = ct[ct.asset_id == well]
    if equipment: d = d[d.equipment == equipment]
    a, b = self.period(months=months, year=year); d = d[(d.ts >= a) & (d.ts <= b)].sort_values("ts", ascending=False)
    m = self.ds.m.set_index("maintenance_id")
    rows = [{"Repair": r.maintenance_id, "Date": str(r.ts.date()), "Equipment": r.equipment, "Issue": m.loc[r.maintenance_id, "issue"], "Root cause (quote)": r.root_cause, "Cost (USD)": int(r.cost)} for r in d.itertuples()]
    notes = [f"{well}: {len(rows)} repair report(s) with a root cause" + (f" for {equipment}" if equipment else "") + "."] if rows else [f"No repair report with a root cause for {well}" + (f" / {equipment}" if equipment else "") + "."]
    return {"visual": "table", "rows": rows[:40], "citations": [r["Repair"] for r in rows[:40]], "notes": notes}


Engine.root_causes = root_causes
Engine.wells_by_cause = wells_by_cause
Engine.trace = trace
