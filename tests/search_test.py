"""Embedding / hybrid search, really tested: (1) the vector index is sound, (2) ablation: BM25-only vs hybrid on paraphrased questions,
(3) end to end: question -> planner -> search_docs -> written answer. Run: .venv/bin/python tests/search_test.py"""
import os, sys, time
os.environ["TRACE_FILE"] = "/dev/null"; os.environ.setdefault("COPILOT_CLARIFY", "auto")
for l in open(".env"):
    k, v = l.strip().split("=", 1); os.environ.setdefault(k, v)
sys.path.insert(0, ".")
import numpy as np
from copilot.data import Dataset
from copilot.memory import Memory
from copilot.agent import Agent, Engine
from copilot import search
ds = Dataset("data/repo/sample-data"); e = Engine(ds, Memory(":memory:")); a = Agent(e)
ITEMS = []
def check(i, desc, ok, info=""):
    ITEMS.append({"id": i, "desc": desc, "ok": bool(ok), "info": str(info)[:300]}); print(("PASS " if ok else "FAIL ") + i, desc, "" if ok else info)

# 1. the vector index
e.search_docs("warm up"); V, ch = e._vec, e._chunks
check("E1", "every chunk has an embedding (768-d, unit length)", V is not None and V.shape == (len(ch), 768) and abs(np.linalg.norm(V, axis=1) - 1).max() < 1e-3, None if V is None else (V.shape, len(ch)))
q = np.array(search._embed(["how quickly must a leak be contained"], "RETRIEVAL_QUERY")[0], dtype=np.float32); q /= np.linalg.norm(q)
sop = [i for i, c in enumerate(ch) if c["kind"] == "manual/sop"]                       # cosine alone, among the governing documents
top = sorted(sop, key=lambda i: -float(V[i] @ q))[:3]
check("E2", "a live-embedded query lands on the right SOP section by cosine alone (SR-02: containment in 4 hours)", any("spill-response" in ch[i]["doc"] for i in top), [(ch[i]["doc"].split("/")[-1], ch[i]["title"][:30]) for i in top])
t = time.time(); e.search_docs("warm again"); check("E3", "second search uses the on-disk cache (no re-embedding of the corpus)", time.time() - t < 8, f"{time.time() - t:.1f}s")

# 2. ablation on paraphrases (no shared keywords with the source text)
CASES = [("how quickly must a leak be contained after it is found", "spill-response-sop", "4 hours"), ("how long do we have to send the written notice to the regulator", "spill-response-sop", "24 hours"),
         ("what temperature difference means a T350 well is running", "T350", "20"), ("when must a pump jack that keeps failing be analysed for its underlying cause", "T200", "root-cause"),
         ("how often must the pipe from the well be pressure tested each year", "regulatory-compliance-sop", "integrity test"), ("who must be told if a well stays stopped for two weeks", "regulatory-compliance-sop", "14 consecutive"),
         ("what gas level on site means no welding is allowed", "field-work-sop", "LEL"), ("how long do we have to get the agency to confirm the clean-up", "spill-response-sop", "60 days")]
def hit(rows, doc, key): return any(doc in r["doc"] and key.lower() in (r["snippet"] + r.get("section", "")).lower() or doc in r["doc"] for r in rows[:5])
def run(vec_on):
    saved = e._vec
    if not vec_on: e._vec = None
    try: return [hit(e.search_docs(q, 5)["rows"], d, k) for q, d, k in CASES]
    finally: e._vec = saved
bm, hy = run(False), run(True)
check("E4", f"hybrid finds the right document for paraphrases: {sum(hy)}/{len(CASES)} (BM25 only: {sum(bm)}/{len(CASES)})", sum(hy) >= sum(bm) and sum(hy) >= 6, (bm, hy))
check("E5", "embeddings add value: at least one paraphrase BM25-only misses but hybrid finds", any(h and not b for b, h in zip(bm, hy)), (bm, hy))

# 3. end to end through the agent (planner -> search_docs -> writer)
for i, (question, doc, key) in enumerate([("What must happen within how many hours after a reportable spill is found, according to our procedures?", "spill-response-sop", "24"),
                                         ("What do the manuals say about when a T350 well counts as producing?", "T350", "20")], 6):
    o = a.ask("U-201", f"e{i}", question); used = o["plan"].get("tool") == "search_docs"
    vec = any("text-embedding" in n for n in o.get("notes", []))
    check(f"E{i}", f"agent called search_docs, hybrid used the embeddings, and the answer is right ({key})", used and vec and key in o["text"], (o["plan"].get("tool"), o.get("notes"), o["text"][:150]))
# 4. Chroma (the vector store) + the embedding cache behind it
col = e._col
check("E8", "Chroma holds every chunk (persistent collection)", col is not None and col.count() == len(ch), None if col is None else (col.count(), len(ch)))
agree = []
for qtext in [c[0] for c in CASES]:
    qv = np.array(search._embed([qtext], "RETRIEVAL_QUERY")[0], dtype=np.float32); qv /= np.linalg.norm(qv)
    npy = set(np.argsort(-(V @ qv))[:10]); idx = {c["id"]: i for i, c in enumerate(ch)}
    agree.append(len(npy & {idx[x] for x in col.query(query_embeddings=[qv.tolist()], n_results=10)["ids"][0]}))
check("E9", "Chroma agrees with the exact numpy cosine ranking (avg top-10 overlap >= 9)", sum(agree) / len(agree) >= 9, agree)
r = col.query(query_embeddings=[V[0].tolist()], n_results=15, where={"well": "WELL-0001"})
check("E10", "metadata filter: a well-filtered query returns only that well's chunks", r["ids"][0] and all(m["well"] == "WELL-0001" for m in r["metadatas"][0]), r["metadatas"][0][:2])
t = time.time(); e2 = Engine(ds, Memory(":memory:")); e2.search_docs("persistence check"); dt = time.time() - t
check("E11", "a fresh engine reopens the persisted Chroma collection and the cache (no re-embedding, no rebuild)", dt < 20 and e2._col.count() == len(ch), f"{dt:.1f}s")
o = a.ask("U-201", "e12", "Why did the flowline fail on WELL-0001 according to the repair reports?")
check("E12", "a 'why did it fail on WELL-X' question gets the repair reports' root causes (tool root_causes or well-filtered search)", o["plan"].get("tool") in ("root_causes", "search_docs") and ("corrosion" in o["text"].lower() or "coupling" in o["text"].lower()), (o["plan"].get("tool"), o["text"][:150]))
print("FAILS:", sum(not i["ok"] for i in ITEMS)); sys.path.insert(0, "tests"); import _results; _results.save("embeddings", ITEMS)
