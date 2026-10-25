"""Read-only audit data for the UI: traces, data lineage and ingest health, rules, tools, prompts, memory, evaluations, health."""
import glob
import json
import os
import re
import time

from . import agent as A
from .data import TODAY_ISO

START = time.time()


def traces(limit=150):
    path = os.environ.get("TRACE_FILE", "traces.jsonl")
    if not os.path.exists(path) or path == "/dev/null": return []
    with open(path) as f: lines = f.readlines()[-limit:]
    out = []
    for l in reversed(lines):
        try: out.append(json.loads(l))
        except ValueError: continue
    return out


def ingest(ds, store_path="data/store.duckdb"):
    ids_i = set(ds.i.inspection_id)
    orphans = {"repairs pointing to a missing inspection": int(ds.m.triggered_by_inspection_id.dropna().map(lambda x: x not in ids_i).sum()),
               "regulator events pointing to a missing inspection": int(ds.r.related_inspection_id.dropna().map(lambda x: x not in ids_i).sum()),
               "corrections pointing to a missing inspection": int(ds.n.inspection_id.dropna().map(lambda x: x not in ids_i).sum()) if "inspection_id" in ds.n else 0,
               "repairs with a report_file but no report text": int(sum(1 for m in ds.m.itertuples() if isinstance(m.report_file, str) and m.maintenance_id not in ds.reports))}
    tables = [{"table": "wells", "rows": len(ds.w), "from": "assets/*/metadata.json"}, {"table": "inspections", "rows": len(ds.i), "from": "assets/*/inspections.jsonl", "range": f"{ds.i.ts.min().date()} to {ds.i.ts.max().date()}"},
              {"table": "maintenance", "rows": len(ds.m), "from": "assets/*/maintenance.jsonl", "range": f"{ds.m.ts.min().date()} to {ds.m.ts.max().date()}"},
              {"table": "regulatory_events", "rows": len(ds.r), "from": "assets/*/regulatory-events.jsonl"}, {"table": "human_notes", "rows": len(ds.n), "from": "assets/*/context.jsonl"},
              {"table": "repair reports (text)", "rows": len(ds.reports), "from": "assets/*/maintenance-reports/*.md", "parsed": f"containment hours in {int(ds.m.contain_hours.notna().sum())}"},
              {"table": "documents indexed", "rows": len(ds.docs), "from": "manuals, SOPs, reports, notes"}, {"table": "areas / teams / users", "rows": f"{len(ds.areas)} / {len(ds.teams)} / {len(ds.users)}", "from": "fleet/*.json"}]
    emb = ".cache/emb.npz"
    return {"roots": ds.roots, "today": TODAY_ISO, "tables": tables, "orphans": orphans, "warnings": ds.warnings or ["none: every rule was parsed from the documents"],
            "duckdb": {"path": store_path, "bytes": os.path.getsize(store_path) if os.path.exists(store_path) else None}, "embeddings_cache_bytes": os.path.getsize(emb) if os.path.exists(emb) else None,
            "well_types": {k: int(v) for k, v in ds.w.well_type.value_counts().items()}}


def rules(e):
    ds = e.ds
    reg = [{"rule": f"producing_delta ({k})", "value": f"{v:g} °C", "source": ds.rules["prov"].get(f"producing_delta:{k}", ""), "origin": "parsed from manual"} for k, v in ds.rules["producing_delta"].items()]
    reg += [{"rule": f"rca_count ({k})", "value": v, "source": "T200.md §10 (T350 refers to it)", "origin": "parsed from manual"} for k, v in ds.rules["rca_count"].items()]
    reg += [{"rule": k, "value": f"{v:g}", "source": ds.rules["prov"].get(k, "fleet/sops"), "origin": "parsed from SOP"} for k, v in ds.rules.items() if isinstance(v, float)]
    over = [{"id": f["id"], "rule": f"{f['field']} for {f['scope_id']}", "value": f["corrected"], "by": f["author"], "status": f["status"], "text": f.get("text")} for f in e.mem.facts(kind="rule", include_inactive=True)]
    return {"registry": reg, "overrides": over}


def tools():
    doc = A.TOOLS_DOC
    out = []
    for m in re.finditer(r"^- (\w+)\{([^}]*)\}\s*-> (.*)$", doc, re.M):
        out.append({"name": m.group(1), "args": m.group(2), "description": m.group(3)})
    return out


def prompts(agent):
    return {"router": A.SYSTEM.replace("{areas}", agent.areas).replace("{mode}", agent.mode), "writer": A.WRITER_PROMPT,
            "models": {"primary": os.environ.get("VERTEX_MODEL", "gemini-2.5-flash") if os.environ.get("USE_VERTEX", "1") == "1" else A.MODELS[0], "backend": os.environ.get("COPILOT_BACKEND", "gemini (Vertex AI)"),
                       "fallbacks": A.MODELS, "gemma": os.environ.get("GEMMA_MODEL", "google/gemma-4-26b-a4b-it-maas"), "embeddings": os.environ.get("EMB_MODEL", "text-embedding-005")},
            "guard": "Every WELL/INS/MNT/CTX/REG ID and every number in the written answer must appear in the tool result, every listed row must be mentioned; otherwise regenerate once, then use a deterministic template."}


def memory(mem, ds):
    rows = mem.db.execute("SELECT user_id, count(*) n, max(ts) last FROM convo GROUP BY user_id").fetchall()
    out = []
    for r in rows:
        turns = mem.db.execute("SELECT ts, role, text, entities, tool FROM convo WHERE user_id=? ORDER BY id DESC LIMIT 12", (r["user_id"],)).fetchall()
        out.append({"user": ds.user_name.get(r["user_id"], r["user_id"]), "user_id": r["user_id"], "turns": r["n"], "last": r["last"], "recent": [dict(t) for t in turns]})
    return {"users": out, "note": "Private memory: recall resolves only from the asking user's own turns."}


def evals():
    out = []
    for p in sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "tests", "results", "*.json"))):
        try:
            with open(p) as f: out.append(json.load(f))
        except ValueError: continue
    return out


def health(agent):
    return {"mode": agent.mode, "today": TODAY_ISO, "uptime_s": int(time.time() - START), "llm": dict(A.STATS), "data_roots": agent.e.ds.roots, "wells": int(len(agent.e.ds.w)),
            "facts_logged": len(agent.e.mem.facts(include_inactive=True)), "clarify_mode": agent.mode, "confirm_rows": os.environ.get("CONFIRM_ROWS", "150")}


def answers():
    """Real answers next to the expected facts, from the saved suite results (given scenarios, extra scenarios, design-review dialogues)."""
    out = []
    for suite in evals():
        for i in suite["items"]:
            if suite["suite"] == "answers":
                out.append({"suite": "given (26 questions)", "id": i["id"], "question": i["question"], "expected": i["expected"], "actual": i["actual"], "ok": i.get("ok"), "judge": i.get("judge"),
                            "tool": i.get("tool"), "blocks": i.get("blocks"), "citations": i.get("citations"), "user": i.get("user")})
            elif suite["suite"] == "extra" and i.get("actual"):
                out.append({"suite": "extra (22)", "id": i["id"], "question": i["question"], "expected": i["expected"], "actual": i["actual"], "ok": i["ok"], "tool": i.get("tool"), "judge": i.get("judge")})
            elif suite["suite"] == "design-review" and i.get("answers"):
                last = i["answers"][-1]
                out.append({"suite": "design review (29)", "id": i["id"], "question": last["q"], "expected": i["desc"], "actual": last["a"], "ok": i["ok"], "tool": last.get("tool"), "user": last.get("user"),
                            "dialogue": i["answers"], "info": i.get("info"), "judge": i.get("judge")})
    return out


def context(agent=None):
    """Context engineering, measured: real token counts per answer (from the traces), composition, and the techniques with live numbers."""
    t = [x for x in traces(400) if x.get("context")]
    t.reverse()
    rows = []
    comp = {}
    for x in t:
        c = x["context"]
        for call in c["calls"]:
            for p in call["parts"]: comp[p["name"]] = comp.get(p["name"], 0) + p["tokens"]
        rows.append({"ts": x["ts"][11:19], "question": x["question"][:70], "total": c["total_tokens"], "prompt": c["prompt_tokens"], "output": c["output_tokens"], "calls": len(c["calls"]),
                     "rows_returned": c.get("rows_returned"), "rows_sent": c.get("rows_sent"), "guard": c.get("guard"), "ms": sum(k["ms"] for k in c["calls"]), "blocks": len(x.get("blocks") or [])})
    n = max(1, len(rows)); avg = lambda k: round(sum((r[k] or 0) for r in rows) / n)
    dataset = t[-1]["context"]["dataset_tokens"] if t else (agent.e.ds.data_tokens if agent else 0)
    fixed = round(comp.get("instructions + tools (fixed)", 0) / n)
    sent = [r for r in rows if r["rows_returned"]]
    guards = {}
    for r in rows: guards[r["guard"] or "n/a"] = guards.get(r["guard"] or "n/a", 0) + 1
    avg_total = avg("total")
    tech = [
        {"technique": "Fixed router prompt", "what": "Same instructions + tool catalogue on every call, so the provider can cache it; no dataset content in it", "number": f"~{fixed} tokens per answer, identical each time"},
        {"technique": "Raw data never sent", "what": "Tools compute over the tables; the model sees only the question and a compact result", "number": f"avg {avg_total:,} tokens per answer vs {dataset:,} tokens of source data ({round(100 * avg_total / max(1, dataset), 3)}%)"},
        {"technique": "Conversation trimmed", "what": "Last 4 turns, 400 characters each; long-term memory is entity IDs, not transcript replay", "number": f"avg {round(comp.get('conversation so far', 0) / n)} tokens of history per answer"},
        {"technique": "Result caps for the writer", "what": "At most 30 rows and 7,000 characters of facts reach the writer; the full table goes to the UI directly", "number": (f"{sum(r['rows_returned'] for r in sent)} rows returned, {sum(r['rows_sent'] for r in sent)} sent to the model" if sent else "n/a")},
        {"technique": "Visuals cost no tokens", "what": "Charts, maps, heatmaps, timelines are composed deterministically by blocks.py from the tool result", "number": f"avg {avg('blocks')} blocks per answer, 0 model tokens"},
        {"technique": "Grounding guard", "what": "Prose is checked against the tool result; regenerate once, then a template", "number": ", ".join(f"{k}: {v}" for k, v in guards.items()) or "n/a"},
        {"technique": "Compiled knowledge (wiki)", "what": "A per-well dossier is a few hundred tokens instead of re-reading its records", "number": "facts page ~300-900 tokens vs thousands of raw rows"},
        {"technique": "Thin LLM role", "what": "One routing call, one writing call and one review call per question; typed tools do the arithmetic", "number": f"avg {round(sum(r['calls'] for r in rows) / n, 1)} model calls per answer"}]
    return {"answers": rows[-60:], "n": len(rows), "avg_total": avg_total, "total_tokens": sum(r["total"] for r in rows), "avg_prompt": avg("prompt"), "avg_output": avg("output"), "dataset_tokens": dataset,
            "composition": [{"part": k, "avg_tokens": round(v / n)} for k, v in sorted(comp.items(), key=lambda kv: -kv[1])], "techniques": tech}


def architecture():
    """The diagram pages from docs/DIAGRAMS.md, split into sections for the Architecture view."""
    path = os.path.join(os.path.dirname(__file__), "..", "docs", "DIAGRAMS.md")
    if not os.path.exists(path): return []
    out = []
    for sec in re.split(r"\n## ", open(path).read())[1:]:
        title, _, body = sec.partition("\n")
        diagrams = re.findall(r"```mermaid\n(.*?)```", body, re.S)
        text = re.sub(r"```mermaid.*?```", "", body, flags=re.S).strip()
        out.append({"title": re.sub(r"^\d+\.\s*", "", title.strip()), "text": text[:700], "diagrams": diagrams})
    return out


# ---------- vector store (Chroma) ----------
def _index(agent):
    e = agent.e
    if getattr(e, "_chunks", None) is None:
        e.search_docs("warm up")           # builds BM25 + loads/builds the Chroma collection from the embedding cache
    return e


def vectors(agent):
    import numpy as np
    e = _index(agent); V, ch, col = e._vec, e._chunks, getattr(e, "_col", None)
    if V is None: return {"error": "embeddings unavailable"}
    X = V - V.mean(axis=0); _, _, vt = np.linalg.svd(X, full_matrices=False); P = X @ vt[:2].T          # 2-D PCA of the 768-d vectors
    kinds = {}
    for c in ch: kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
    cache = ".cache/emb.npz"; cdir = os.environ.get("CHROMA_DIR", ".cache/chroma")
    size = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(cdir) for f in fs) if os.path.isdir(cdir) else 0
    meta = {}
    if col is not None:
        try: meta = {k: (str(v) if not isinstance(v, (int, float, str)) else v) for k, v in col.metadata.items()}; cfg = str(col.configuration.get("hnsw")) if hasattr(col, "configuration") else ""
        except Exception: cfg = ""  # noqa: BLE001
    else: cfg = ""
    return {"store": "chroma" if col is not None else "numpy matrix", "chunks": len(ch), "dim": int(V.shape[1]), "kinds": kinds, "model": os.environ.get("EMB_MODEL", "text-embedding-005"), "chroma_path": cdir, "chroma_bytes": size,
            "embedding_cache_bytes": os.path.getsize(cache) if os.path.exists(cache) else None, "collection_metadata": meta, "hnsw": cfg,
            "points": [{"x": round(float(P[i, 0]), 4), "y": round(float(P[i, 1]), 4), "group": ch[i]["kind"], "label": ch[i]["id"][:60]} for i in range(len(ch))]}


def vquery(agent, q, k=10):
    import numpy as np
    from . import search
    e = _index(agent); ch, V, col = e._chunks, e._vec, getattr(e, "_col", None)
    qv = np.array(search._embed([q], "RETRIEVAL_QUERY")[0], dtype=np.float32); qv /= np.linalg.norm(qv)
    cos = V @ qv; top = list(np.argsort(-cos)[:k])
    fused = e.search_docs(q, k)["rows"]
    return {"vector_only": [{"rank": r + 1, "id": ch[i]["id"], "kind": ch[i]["kind"], "cosine": round(float(cos[i]), 3), "text": ch[i]["text"][:200]} for r, i in enumerate(top)],
            "hybrid": [{"rank": r + 1, "doc": x["doc"], "kind": x["kind"], "section": x["section"], "snippet": x["snippet"][:200]} for r, x in enumerate(fused)], "store": "chroma" if col is not None else "numpy"}


def vbrowse(agent, kind="", q="", limit=30):
    e = _index(agent); col = getattr(e, "_col", None)
    if col is None: return []
    where = {"kind": kind} if kind else None
    got = col.get(where=where, limit=int(limit) * (6 if q else 1), include=["documents", "metadatas"])
    rows = [{"id": i, "kind": m.get("kind"), "well": m.get("well"), "well_type": m.get("well_type"), "text": (d or "")[:260]} for i, d, m in zip(got["ids"], got["documents"], got["metadatas"])]
    if q: rows = [r for r in rows if q.lower() in (r["id"] + r["text"]).lower()]
    return rows[: int(limit)]


# ---------- QA: how answers are verified, and the real results ----------
QA_LAYERS = [
    {"suite": "golden", "layer": "1 · Deterministic", "title": "Golden checks", "command": "python tests/golden.py",
     "why": "The challenge publishes expected answers. These tests prove the TOOLS return exactly those values, with no model involved, so any later wrong answer is a routing or writing problem, never an arithmetic one.",
     "how": "Each check calls an engine tool directly (well_status, downtime, spills, compliance, RCA...) and compares with the value from the challenge document. A SQL query on the persisted DuckDB store cross-checks one result a second way.",
     "truth": "Expected values copied from the challenge's example-questions document."},
    {"suite": "extra", "layer": "1 · Deterministic", "title": "22 extra scenarios (11 medium, 11 complex)", "command": "python tests/extra/run.py",
     "why": "The 18 given questions are few and public, so we added harder, real-world-style questions (repeat failures, RC-01/02/03 compliance, spill reporting lateness, cost per downtime day...) and check them against ground truth the tools did not produce.",
     "how": "Each question goes through the real agent (planner picks a tool and arguments); the returned rows are compared with a value computed by separate pandas code in tests/extra/truth.py that reads the raw files and does not import the copilot.",
     "truth": "Independent pandas ground truth from the raw JSONL files."},
    {"suite": "design-review", "layer": "2 · Behaviour", "title": "29 stateful scenarios (10 core)", "command": "python tests/chat/run.py [core]",
     "why": "Memory, corrections and clarification are behaviours, not facts. They need multi-step dialogues across users and chats: a correction by one user must change another user's answer, undo must restore it, recall must resolve months later, a big change must ask first.",
     "how": "Each scenario builds a fresh in-memory copilot, plays a short dialogue through the real agent, then asserts on the resulting state (effective data, corrections log statuses, options returned) and on values recomputed independently with pandas where possible.",
     "truth": "Behavioural assertions + independent pandas values; the dialogue and every real answer are saved."},
    {"suite": "blocks", "layer": "1 · Deterministic", "title": "Visualization composition", "command": "python tests/blocks_test.py",
     "why": "Each answer should carry several visualizations (KPIs, charts, map, timeline). The composer is deterministic code, so it is tested without a model.",
     "how": "Tool results are turned into blocks and the test asserts the block types and key contents (for example the bar chart holds exactly the three expected wells and the heatmap totals match Q8).", "truth": "Known tool outputs."},
    {"suite": "sql-tool", "layer": "3 · Safety", "title": "Open-ended SQL tool", "command": "python tests/sql_test.py",
     "why": "A model writing SQL is the riskiest feature. It must be read-only and its answers must match ground truth.",
     "how": "Four generated queries are compared with pandas results; seven unsafe statements (DROP, DELETE, COPY, PRAGMA, multi-statement, file reads) must be rejected by the validator; a covered question must not route to SQL.", "truth": "Independent pandas values; validator rules."},
    {"suite": "embeddings", "layer": "3 · Retrieval", "title": "Embeddings and Chroma", "command": "python tests/search_test.py",
     "why": "Hybrid search is only worth having if the vectors are sound and add value over keyword search alone.",
     "how": "Checks every chunk has a 768-d unit vector, that Chroma agrees with exact cosine ranking, that metadata filters work, and runs an ablation: BM25-only vs hybrid on eight paraphrased questions. Two questions then go planner > search > answer end to end.", "truth": "Known source passages in the manuals and SOPs."},
    {"suite": "context", "layer": "3 · Accounting", "title": "Token accounting", "command": "python tests/context_test.py",
     "why": "Context engineering claims (the model sees a tiny fraction of the data) must be measured, not asserted.",
     "how": "Asserts real API token counts per call, that prompt parts add up, that the question is a tiny part of the router prompt, and that large results are capped before the writer.", "truth": "Counts returned by the model API."},
    {"suite": "critic", "layer": "3 · Runtime guard", "title": "Critic sub-agent", "command": "python tests/critic_test.py",
     "why": "The critic is a second model that reviews drafts. It needs its own test: does it flag planted mistakes and leave a correct answer alone?",
     "how": "Four hand-written drafts against fixed facts: one correct, one that excludes a listed row, one with a wrong number, one that hides a rule-vs-manual conflict.", "truth": "Constructed cases with a known right/wrong label."},
    {"suite": "router-gemini", "layer": "4 · Models", "title": "Router benchmark, Gemini", "command": "python tests/bench_router.py",
     "why": "The planner's tool choice is the first thing that can go wrong. It is measured on all 40 question types.", "how": "Only the planner call runs (no writer). The chosen tool and key arguments are compared with the expected ones.", "truth": "Expected tool and arguments written per question."},
    {"suite": "router-gemma", "layer": "4 · Models", "title": "Router benchmark, Gemma 4", "command": "COPILOT_BACKEND=gemma python tests/bench_router.py",
     "why": "Shows how far a small open model gets when the LLM's job is thin.", "how": "Same benchmark with Gemma 4 26B-A4B on Vertex.", "truth": "Same expectations."},
    {"suite": "answers", "layer": "5 · Judge", "title": "LLM judge on the 26 given questions", "command": "python tests/qa/run_answers.py --judge",
     "why": "Numbers can be right while the answer is badly written, incomplete or silent about a conflict. A stronger, different model reads each answer against the expected facts.",
     "how": "The 26 given questions run through the agent in order with fresh memory. Gemini 2.5 Pro (not the writer) scores correctness, grounding, completeness, honesty and clarity 1-5 and gives a verdict, seeing the text and the visuals/data shown.", "truth": "Expected facts from the challenge document (tests/qa/expected.py)."},
    {"suite": "ui-syntax", "layer": "3 · Safety", "title": "UI modules parse", "command": "python tests/ui_syntax_test.py",
     "why": "A missing parenthesis once produced a blank page; this makes it impossible to ship.", "how": "Every front-end module is parsed by Node.", "truth": "Parser."}]


def qa(agent=None):
    import importlib.util
    res = {s["suite"]: s for s in evals()}
    hist = {}
    p = os.path.join(os.path.dirname(__file__), "..", "tests", "results", "history.jsonl")
    if os.path.exists(p):
        for line in open(p):
            try: r = json.loads(line)
            except ValueError: continue
            hist.setdefault(r["suite"], []).append(r)
    layers = []
    for L in QA_LAYERS:
        r = res.get(L["suite"]); h = hist.get(L["suite"], [])
        layers.append({**L, "result": ({"passed": r["passed"], "total": r["total"], "ran_at": r["ran_at"], "failing": [i["id"] for i in r["items"] if not i["ok"]]} if r else None),
                       "history": [{"ts": x["ts"], "passed": x["passed"], "total": x["total"]} for x in h][-12:], "varies": len({x["passed"] for x in h}) > 1})
    judged_items = []   # (suite label, item) for every suite the judge has graded
    for key, label in (("answers", "18 given scenarios (26 questions)"), ("extra", "22 extra scenarios"), ("design-review", "29 design-review scenarios")):
        for i in (res.get(key) or {}).get("items", []): judged_items.append((label, i))
    graded = [(l, i) for l, i in judged_items if i.get("judge", {}).get("scores")]
    judge = None
    if graded:
        js = [i["judge"] for _, i in graded]; crit = list(js[0]["scores"])
        per = {}
        for l, i in judged_items:
            p_ = per.setdefault(l, {"suite": l, "scenarios": 0, "judged": 0, "pass": 0, "partial": 0, "fail": 0, "not_judged": []})
            p_["scenarios"] += 1
            v = i.get("judge", {}).get("verdict") if i.get("judge", {}).get("scores") else None
            if v: p_["judged"] += 1; p_[v] += 1
            else: p_["not_judged"].append(i["id"])
        judge = {"model": (res.get("answers") or {}).get("judge_model") or (res.get("extra") or {}).get("judge_model"), "judged": len(js), "of": len(judged_items), "per_suite": list(per.values()),
                 "verdicts": {v: sum(1 for j in js if j.get("verdict") == v) for v in ("pass", "partial", "fail")}, "avg": {c: round(sum(j["scores"].get(c, 0) for j in js) / len(js), 2) for c in crit},
                 "not_judged": [f"{l.split(' ')[0]}·{i['id']}" for l, i in judged_items if not i.get("judge", {}).get("scores")],
                 "weakest": sorted(({"id": f"{l.split(' ')[0]}·{i['id']}", "verdict": i["judge"]["verdict"], "issues": i["judge"].get("issues", [])} for l, i in graded if i["judge"].get("verdict") != "pass"), key=lambda x: x["id"])}
    rub = ""
    rp = os.path.join(os.path.dirname(__file__), "..", "tests", "qa", "rubric.py")
    if os.path.exists(rp):
        spec = importlib.util.spec_from_file_location("rubric", rp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); rub = m.RUBRIC
    guards = {}
    for x in traces(400):
        g = (x.get("context") or {}).get("guard")
        if g: guards[g] = guards.get(g, 0) + 1
    return {"layers": layers, "judge": judge, "rubric": rub, "runtime_guards": guards,
            "limitations": ["The scenario suites were written by the builder and tuned against failures seen on the same questions: passing them is not evidence of generalising. The unseen final questions are the real test.",
                            "Several checks depend on a model (planner, writer, critic, judge), so results can vary between runs; the history above shows which suites varied.",
                            "The judge is a model from the same vendor family as the writer (a stronger tier), and it is strict; its verdicts are evidence, not proof.",
                            "Expected facts were transcribed from the challenge document by the builder.",
                            "A judge run can fail on a transient model error; such items are listed as 'not judged', never counted as a pass or a fail."]}
