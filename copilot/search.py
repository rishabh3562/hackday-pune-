"""Hybrid document search: BM25 (exact tokens like SR-01, MNT-0001-029) + embeddings (paraphrase), merged by reciprocal rank.
Chunks carry applicability metadata (well, well type) so a well's own reports and its type's manual rank first."""
import hashlib
import os
import re
from concurrent.futures import ThreadPoolExecutor

import httpx
import numpy as np

from .tools import Engine

EMB_MODEL = os.environ.get("EMB_MODEL", "text-embedding-005")
CACHE = os.environ.get("EMB_CACHE", ".cache/emb")
GCP_PROJECT = os.environ.get("GCP_PROJECT", "omni-505707")
TOK = lambda t: re.findall(r"[a-z0-9\-]+", t.lower())


def _passages(doc_id, text):
    """Manuals/SOPs -> one chunk per subsection (### ) and one per protocol row (| **SR-02** |), each prefixed with its document and section so it stands alone."""
    out = []
    name = doc_id.split("/")[-1].replace(".md", "")
    for sec in re.split(r"\n(?=## )", text):
        head = sec.strip().split("\n")[0].lstrip("# ").strip()
        for sub in re.split(r"\n(?=### )", sec):
            sh = sub.strip().split("\n")[0].lstrip("# ").strip()
            rows = [l for l in sub.split("\n") if re.match(r"\|\s*\*\*[A-Z]{2}-\d\d\*\*", l)]
            if rows:                                              # a protocol table: one passage per protocol
                out += [(f"{name} / {head}: {r.strip('| ')}", r.strip("| ")[:60]) for r in rows]
            elif len(sub.strip()) > 40:
                out.append((f"{name} / {head}" + (f" / {sh}" if sh != head else "") + f"\n{sub.strip()}", sh or head))
    return out


def _chunks(ds):
    out = []
    for doc_id, kind, text in ds.docs:
        well = re.search(r"WELL-\d{4}", doc_id + " " + text[:200])
        wtype = re.search(r"well-types/(T\d+)", doc_id)
        parts = _passages(doc_id, text) if kind == "manual/sop" else [(text, text.strip().split("\n")[0][:80])]
        for i, (body, title) in enumerate(parts):
            if len(body.strip()) < 40: continue
            out.append({"id": f"{doc_id}#{i}", "doc": doc_id, "kind": kind, "well": well.group(0) if kind != "manual/sop" and well else None,
                        "well_type": wtype.group(1) if wtype else None, "title": title[:80], "text": body[:6000]})
    return out


def _window(text, query, size=900):
    """The part of a long chunk that best matches the query (so the key line is never cut off)."""
    if len(text) <= size: return text
    q = set(TOK(query)); toks = list(re.finditer(r"\S+", text))
    best, pos = -1, 0
    for k in range(0, len(toks), 8):
        a = toks[k].start(); seg = text[a:a + size]
        sc = sum(1 for t in TOK(seg) if t in q)
        if sc > best: best, pos = sc, a
    return ("…" if pos else "") + text[pos:pos + size]


def _embed(texts, task):
    import google.auth
    import google.auth.transport.requests as tr
    c, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    c.refresh(tr.Request())
    url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{GCP_PROJECT}/locations/us-central1/publishers/google/models/{EMB_MODEL}:predict"

    def one(batch):
        r = httpx.post(url, headers={"Authorization": "Bearer " + c.token}, timeout=120,
                       json={"instances": [{"content": t[:6000], "task_type": task} for t in batch]})
        return [p["embeddings"]["values"] for p in r.json()["predictions"]]
    batches = [texts[i:i + 20] for i in range(0, len(texts), 20)]
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(one, batches))
    return [v for b in res for v in b]


def _chroma(ch, vec, keys):
    """Persistent Chroma collection built from the embedding cache (so nothing is re-embedded). Rebuilt only when the chunk set changes."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=os.environ.get("CHROMA_DIR", ".cache/chroma"))
        fp = hashlib.md5("".join(keys).encode()).hexdigest()
        try:
            col = client.get_collection("chunks")
            if col.metadata.get("fp") == fp: return col
            client.delete_collection("chunks")
        except Exception:  # noqa: BLE001  (collection does not exist yet)
            pass
        col = client.create_collection("chunks", metadata={"fp": fp, "model": EMB_MODEL},   # high-recall HNSW: ~1.7k vectors, so exploring widely is cheap and keeps results exact in practice
                                       configuration={"hnsw": {"space": "cosine", "ef_construction": 400, "ef_search": 1500, "max_neighbors": 48}})
        for i in range(0, len(ch), 400):
            sl = ch[i:i + 400]
            col.add(ids=[c["id"] for c in sl], embeddings=vec[i:i + 400].tolist(), documents=[c["text"][:2000] for c in sl],
                    metadatas=[{"doc": c["doc"], "kind": c["kind"], "well": c["well"] or "", "well_type": c["well_type"] or ""} for c in sl])
        return col
    except Exception:  # noqa: BLE001  (fall back to the in-memory matrix)
        return None


def build(self):
    from rank_bm25 import BM25Okapi
    ch = _chunks(self.ds)
    self._chunks = ch
    self._bm25 = BM25Okapi([TOK(c["title"] + " " + c["text"]) for c in ch])
    self._vec = None
    try:
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        keys = [hashlib.md5((EMB_MODEL + c["text"]).encode()).hexdigest() for c in ch]
        cached = {}
        if os.path.exists(CACHE + ".npz"):
            z = np.load(CACHE + ".npz", allow_pickle=True)
            cached = dict(zip(z["keys"].tolist(), z["vecs"]))
        missing = [i for i, k in enumerate(keys) if k not in cached]
        if missing:
            vecs = _embed([ch[i]["text"] for i in missing], "RETRIEVAL_DOCUMENT")
            for i, v in zip(missing, vecs):
                cached[keys[i]] = np.array(v, dtype=np.float32)
            np.savez(CACHE + ".npz", keys=np.array(list(cached)), vecs=np.stack(list(cached.values())))
        m = np.stack([cached[k] for k in keys])
        self._vec = m / np.linalg.norm(m, axis=1, keepdims=True)
        self._col = _chroma(ch, self._vec, keys) if os.environ.get("VECTOR_STORE", "chroma") == "chroma" else None
    except Exception as ex:  # noqa: BLE001  (BM25-only fallback)
        self._vec_error = str(ex)[:120]


def search_docs(self, query, k=5, well=None):
    if getattr(self, "_chunks", None) is None:
        build(self)
    ch = self._chunks
    m = re.search(r"WELL-\d{4}", query)
    well = well or (m.group(0) if m else None)
    wtype = self.ds.w.loc[well, "well_type"] if well and well in self.ds.w.index else None
    lex = np.array(self._bm25.get_scores(TOK(query)))
    ranks = {}
    lists = [list(np.argsort(-lex)[:50])]                                            # BM25 ranking
    store = "bm25 only"
    if self._vec is not None:
        qv = np.array(_embed([query], "RETRIEVAL_QUERY")[0], dtype=np.float32); qv /= np.linalg.norm(qv)
        col = getattr(self, "_col", None)
        if col is not None:                                                         # Chroma: global ranking + (for a named well) a metadata-filtered ranking
            idx = {c["id"]: i for i, c in enumerate(ch)}
            lists.append([idx[x] for x in col.query(query_embeddings=[qv.tolist()], n_results=50)["ids"][0]])
            if well: lists.append([idx[x] for x in col.query(query_embeddings=[qv.tolist()], n_results=15, where={"well": well})["ids"][0]])
            store = f"chroma ({col.count()} chunks)"
        else:
            lists.append(list(np.argsort(-(self._vec @ qv))[:50])); store = "numpy matrix"
    for lst in lists:
        for r, i in enumerate(lst):
            ranks[i] = ranks.get(i, 0) + 1 / (60 + r)
    about_record = bool(re.search(r"(INS|MNT|CTX|REG)-\d|\breport\b|\bnote\b", query, re.I))
    for i in ranks:   # applicability boost: this well's own records, then its type's manual, then fleet SOPs
        c = ch[i]
        if not about_record and c["kind"] == "manual/sop":
            ranks[i] *= 1.6                      # a rule/procedure question: the governing document beats a similar-sounding repair report
        if well and c["well"] == well:
            ranks[i] *= 1.5
        elif wtype and c["well_type"] == wtype:
            ranks[i] *= 1.3
    top = sorted(ranks, key=lambda i: -ranks[i])[:k]
    rows = [{"doc": ch[i]["doc"], "kind": ch[i]["kind"], "section": ch[i]["title"], "snippet": _window(ch[i]["text"], query)} for i in top]
    prof = []
    if well and well in self.ds.w.index:        # name the governing document: the well's type decides which manual applies
        wt, ar = self.ds.w.loc[well, "well_type"], self.ds.area_name.get(self.ds.w.loc[well, "area_id"])
        prof.append(f"{well} is a {wt} well in {ar}; the {wt} manual applies to it." + (f" Producing threshold for {wt}: {self.ds.rules['producing_delta'].get(wt):g} °C above ambient ({self.ds.rules['prov'].get(f'producing_delta:{wt}')})." if re.search(r"temperature|producing|threshold|rise", query, re.I) else ""))
    return {"visual": "text", "rows": rows, "citations": [r["doc"] for r in rows],
            "notes": prof + [f"hybrid search: BM25 + {EMB_MODEL} vectors in {store}" if self._vec is not None else "hybrid search: BM25 only (embeddings unavailable)"], "vector_store": store}


Engine.search_docs = search_docs
