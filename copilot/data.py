"""Load a dataset directory (sample or test) into pandas frames; pull rules out of the manuals/SOPs."""
import glob
import json
import os
import re
import warnings

import pandas as pd

# One config value for "today"; windows ("last 4 months") are anchored on the previous day = the last day of data,
# which reproduces the stated Q6 window (16 Jun to 16 Oct).
TODAY = pd.Timestamp(os.environ.get("COPILOT_TODAY", "2026-10-17"), tz="UTC")
ANCHOR = TODAY - pd.Timedelta(days=1)
TODAY_ISO = str(TODAY.date())


def _jsonl(path):
    out = []
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
    return out


def _json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _section(path, pattern):
    """'<file> §<heading number or protocol>' of the first match of pattern in a document (for citations)."""
    try:
        raw = _read(path)
        flat = re.sub(r"\s+", " ", raw)
        m = re.search(pattern, flat)
        if not m:
            return os.path.basename(path)
        before = flat[:m.start()]
        heads = re.findall(r"## (\d+(?:\.\d+)*)\.? ", before) + re.findall(r"### (\d+(?:\.\d+)*) ", before)
        proto = re.findall(r"\*\*([A-Z]{2}-\d\d)\*\*", flat[max(0, m.start() - 400):m.end()])
        sec = heads[-1] if heads else ""
        return os.path.basename(path) + (f" §{sec}" if sec else "") + (f" ({proto[-1]})" if proto else "")
    except Exception:  # noqa: BLE001
        return os.path.basename(path)


def parse_rules(root):
    """Thresholds come from the document text, never hardcoded in the tools."""
    rules = {"producing_delta": {}, "rca_count": {}, "prov": {}}
    for p in glob.glob(f"{root}/fleet/well-types/*.md"):
        wt = os.path.basename(p)[:-3]
        t = _read(p)
        m = re.search(r"at least \*\*(\d+)\s*°C\s*above", t.replace("\n", " "))
        if not m:
            m = re.search(r"at\s+least\s+\*\*(\d+)\s*°C\s+above", re.sub(r"\s+", " ", t))
        if m:
            rules["producing_delta"][wt] = float(m.group(1))
            rules["prov"][f"producing_delta:{wt}"] = _section(p, r"at least \*\*\d+\s*°C\s*above")
        m = re.search(r"(Three|Two|Four|\d+) or more \*\*corrective\*\*", t) or re.search(
            r"RCA after (three|two|four|\d+) corrective", re.sub(r"\s+", " ", t))
        words = {"one": 1, "two": 2, "three": 3, "four": 4}
        if m:
            g = m.group(1).lower()
            rules["rca_count"][wt] = words.get(g) or int(g)
    for wt, dflt in (("T200", 15.0), ("T350", 20.0)):
        if os.path.exists(f"{root}/fleet/well-types/{wt}.md") and wt not in rules["producing_delta"]:
            warnings.warn(f"producing delta for {wt} not parsed; using {dflt}")
            rules["producing_delta"][wt] = dflt
    # T350 manual refers to T200 section 10 for RCA
    for wt in rules["producing_delta"]:
        rules["rca_count"].setdefault(wt, rules["rca_count"].get("T200", 3))
    def grab(path, pattern, default, name):
        """Regex a number out of a document; warn and fall back to the sample-data value if the wording differs."""
        try:
            return float(re.search(pattern, re.sub(r"\s+", " ", _read(path))).group(1))
        except Exception:  # noqa: BLE001
            warnings.warn(f"rule '{name}' not found in {path}; using default {default}")
            return default
    sp, rc = f"{root}/fleet/sops/spill-response-sop.md", f"{root}/fleet/sops/regulatory-compliance-sop.md"
    rules["reportable_bbl"] = grab(sp, r"\| Reportable \| (\d+(?:\.\d+)?) bbl", 5.0, "reportable_bbl")
    rules["major_bbl"] = grab(sp, r"\| Major \| (\d+(?:\.\d+)?) bbl or more", 25.0, "major_bbl")
    rules["report_hours"] = grab(sp, r"within \*\*(\d+) hours\*\* of discovery", 24.0, "report_hours")
    # revision-dependent deadline: "(24 hours for spills discovered before 1 Jan 2027)" -> older limit + cut-over date
    m = re.search(r"\((\d+) hours for spills discovered before (\d+ \w+ \d{4})\)", re.sub(r"\s+", " ", _read(sp)) if os.path.exists(sp) else "")
    rules["report_hours_before"], rules["report_hours_cutover"] = (float(m.group(1)), str(pd.Timestamp(m.group(2)).date())) if m else (None, None)
    rules["major_report_hours"] = grab(sp, r"or within \*\*(\d+) hours\*\* for a major", 2.0, "major_report_hours")
    rules["contain_hours"] = grab(sp, r"contained within \*\*(\d+) hours\*\*", 4.0, "contain_hours")
    rules["verify_days"] = grab(sp, r"verified within (\d+) days", 60.0, "verify_days")
    rules["nov_days"] = grab(rc, r"answered within \*\*(\d+) days", 30.0, "nov_days")
    rules["inspect_days"] = grab(rc, r"inspected at least once every \*\*(\d+) days", 14.0, "inspect_days")
    rules["down_report_days"] = 14.0
    rules["prov"].update({
        "reportable_bbl": _section(sp, r"\| Reportable \|"), "report_hours": _section(sp, r"within \*\*\d+ hours\*\* of discovery"),
        "contain_hours": _section(sp, r"contained within \*\*\d+ hours"), "verify_days": _section(sp, r"verified within \d+ days"),
        "nov_days": _section(rc, r"answered within \*\*\d+ days"), "inspect_days": _section(rc, r"inspected at least once every")})
    return rules


class Dataset:
    def __init__(self, *roots):
        self.roots = [self.find_root(r) for r in roots]
        self.warnings = []
        # size of everything the copilot could read, in tokens (chars/4): the baseline for "how much context did this answer NOT need"
        self.data_tokens = sum(os.path.getsize(f) for r in self.roots for f in glob.glob(f"{r}/**/*", recursive=True) if os.path.isfile(f) and f.endswith((".jsonl", ".json", ".md"))) // 4
        self.wells, self.insp, self.maint, self.reg, self.notes = [], [], [], [], []
        self.reports = {}      # maintenance_id -> text
        self.docs = []         # (doc_id, kind, text) for search
        self.areas, self.teams, self.users = [], [], []
        self.rules = {"producing_delta": {}, "rca_count": {}}
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", UserWarning)
            for r in self.roots:
                self._load(r)
            self.warnings = [str(w.message) for w in caught if issubclass(w.category, UserWarning)]
        self.type_hist = {w['asset_id']: w['type_history'] for w in self.wells if w.get('type_history')}
        self._frames()

    @staticmethod
    def find_root(root):
        """Accept the dataset root, its parent, or a nested folder: locate the dir holding fleet/ and assets/."""
        for cand in [root] + glob.glob(f"{root}/*") + glob.glob(f"{root}/*/*"):
            if os.path.isdir(f"{cand}/fleet") and os.path.isdir(f"{cand}/assets"):
                return cand
        raise FileNotFoundError(f"no fleet/ + assets/ under {root}")

    def _load(self, root):
        root = self.find_root(root)
        areas = _json(f"{root}/fleet/areas.json")
        for key, dst, items in (("area_id", self.areas, areas["areas"]), ("team_id", self.teams, areas["teams"]),
                                ("user_id", self.users, _json(f"{root}/fleet/users.json")["users"])):
            by = {x[key]: x for x in dst}
            for x in items:   # later root wins; area well lists are merged
                if key == "area_id" and x[key] in by:
                    x = {**x, "asset_ids": sorted(set(by[x[key]].get("asset_ids", [])) | set(x.get("asset_ids", [])))}
                by[x[key]] = x
            dst[:] = list(by.values())
        rules = parse_rules(root)
        for k, v in rules.items():
            if isinstance(v, dict):
                self.rules.setdefault(k, {}).update(v)
            else:
                self.rules[k] = v
        for p in glob.glob(f"{root}/fleet/**/*.md", recursive=True):
            self.docs.append((os.path.relpath(p, root), "manual/sop", _read(p)))
        for d in sorted(glob.glob(f"{root}/assets/*/")):
            meta = _json(d + "metadata.json")
            self.wells.append(meta)
            self.insp += _jsonl(d + "inspections.jsonl")
            self.maint += _jsonl(d + "maintenance.jsonl")
            self.reg += _jsonl(d + "regulatory-events.jsonl")
            self.notes += _jsonl(d + "context.jsonl")
        for m in self.maint:
            rf = m.get("report_file")
            if rf and m["maintenance_id"] not in self.reports:
                for r in self.roots:
                    for cand in (f"{r}/assets/{m['asset_id']}/{rf}", f"{r}/{rf}"):
                        if os.path.exists(cand):
                            self.reports[m["maintenance_id"]] = _read(cand)
                            break
                    if m["maintenance_id"] in self.reports:
                        break

    def _frames(self):
        w = pd.DataFrame(self.wells).drop_duplicates("asset_id", keep="last")
        w["lat"] = w["location"].map(lambda x: x["lat"])
        w["lon"] = w["location"].map(lambda x: x["lon"])
        self.w = w.set_index("asset_id", drop=False)
        i = pd.DataFrame(self.insp).drop_duplicates("inspection_id", keep="last")
        i["ts"] = pd.to_datetime(i["inspected_at"], utc=True)
        i["well_type"] = i["asset_id"].map(self.w["well_type"])
        i["area_id"] = i["asset_id"].map(self.w["area_id"])
        i["delta"] = i["wellhead_temp_c"] - i["ambient_temp_c"]
        self.i = i.sort_values(["asset_id", "ts"]).reset_index(drop=True)
        m = pd.DataFrame(self.maint).drop_duplicates("maintenance_id", keep="last")
        m["ts"] = pd.to_datetime(m["started_at"], utc=True)
        m["cost_total"] = m["cost_usd"].map(lambda c: (c or {}).get("total", 0))
        m["well_type"] = m["asset_id"].map(self.w["well_type"])
        m["area_id"] = m["asset_id"].map(self.w["area_id"])
        m["contain_hours"] = m["maintenance_id"].map(self._containment)
        self.m = m.sort_values(["asset_id", "ts"]).reset_index(drop=True)
        r = pd.DataFrame(self.reg).drop_duplicates("event_id", keep="last")
        r["ts"] = pd.to_datetime(r["date"], utc=True)
        self.r = r
        n = pd.DataFrame(self.notes).drop_duplicates("note_id", keep="last")
        n["ts"] = pd.to_datetime(n["created_at"], utc=True)
        self.n = n
        self.user_name = {u["user_id"]: u["name"] for u in self.users}
        self.area_name = {a["area_id"]: a["name"] for a in self.areas}
        for mid, t in self.reports.items():
            self.docs.append((mid, "maintenance report", t))
        for _, row in n.iterrows():
            self.docs.append((row["note_id"], "note", f"{row['asset_id']} {row['note_type']}: {row['text']}"))

    def report_limit(self, ts):
        """SR-01 written-notice limit (hours) in force on the discovery date."""
        cut, old = self.rules.get("report_hours_cutover"), self.rules.get("report_hours_before")
        return old if cut and old and pd.Timestamp(ts).tz_convert("UTC").date() < pd.Timestamp(cut).date() else self.rules["report_hours"]

    def _containment(self, mid):
        t = self.reports.get(mid)
        if not t:
            return None
        m = re.search(r"contained about\s+\**([\d.]+)\s*hours", re.sub(r"\s+", " ", t))
        return float(m.group(1)) if m else None
