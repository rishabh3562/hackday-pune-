"""FastAPI app: /api/ask, /api/users, static UI. Dataset dirs come from DATA_DIRS (comma separated)."""
import json
import os

os.environ.setdefault("COPILOT_TODAY", "2027-01-15")     # the test data's 'today'; set COPILOT_TODAY + DATA_DIRS to use another dataset

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent import Agent
from .data import Dataset
from .memory import Memory
from .tools import Engine

roots = os.environ.get("DATA_DIRS", "data/repo/test-data/dataset").split(",")
ds = Dataset(*roots)
try:
    from .store import to_duckdb
    to_duckdb(ds, os.environ.get('STORE_DB', 'data/store.duckdb'))
except Exception as _e:  # noqa: BLE001
    print('duckdb persist skipped:', _e)
mem = Memory(os.environ.get("MEMORY_DB", "memory.db"))
agent = Agent(Engine(ds, mem))
app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:3000'], allow_methods=['*'], allow_headers=['*'])
from .agui import mount as _mount_agui
_mount_agui(app, agent)


class Ask(BaseModel):
    user_id: str
    chat_id: str
    text: str
    mode: str | None = None      # "ask" | "auto": per-request clarification mode (server default if omitted)


@app.get("/api/users")
def users():
    return ds.users


@app.get("/api/areas")
def areas():
    return ds.areas


@app.post("/api/ask")
def ask(a: Ask):
    out = agent.ask(a.user_id, a.chat_id, a.text, mode=a.mode)
    try:
        mem.save_payload(a.user_id, a.chat_id, out)      # so a reopened chat re-renders the answer's visuals
    except Exception as _e:  # noqa: BLE001
        print("chat payload not saved:", _e)
    return out


@app.get("/api/chats")
def chats_list(user_id: str):
    return mem.list_chats(user_id)


@app.get("/api/chats/{chat_id}")
def chats_get(chat_id: str, user_id: str):
    return {"id": chat_id, "turns": mem.get_chat(user_id, chat_id)}


@app.delete("/api/chats/{chat_id}")
def chats_delete(chat_id: str, user_id: str):
    return {"deleted": mem.delete_chat(user_id, chat_id)}


@app.patch("/api/chats/{chat_id}")
def chats_rename(chat_id: str, user_id: str, a: dict):
    title = str(a.get("title", "")).strip()
    if not title:
        raise HTTPException(400, "title required")
    mem.rename_chat(user_id, chat_id, title)
    return {"ok": True}


_briefing_cache = {}


@app.get("/api/briefing")
def briefing_api():
    from .briefing import briefing
    key = mem.db.total_changes            # recompute only after the corrections log changes
    if _briefing_cache.get("key") != key:
        _briefing_cache.update(key=key, data=briefing(agent.e))
    return _briefing_cache["data"]


@app.post("/api/voice/token")
def voice_token(a: dict):
    """Short-lived LiveKit token so the browser can join a room; the voice agent worker (voice/agent.py) joins the same room."""
    from livekit import api as lk
    key, secret, url = os.environ.get("OMNI_LIVEKIT_API_KEY"), os.environ.get("OMNI_LIVEKIT_API_SECRET"), os.environ.get("OMNI_LIVEKIT_URL")
    if not (key and secret and url):
        return {"error": "OMNI_LIVEKIT_URL / OMNI_LIVEKIT_API_KEY / OMNI_LIVEKIT_API_SECRET are not set in .env"}
    uid = a.get("user_id", "U-201")
    room = f"copilot-{uid}-{int(__import__('time').time())}"
    tok = (lk.AccessToken(key, secret).with_identity(f"user-{uid}").with_name(ds.user_name.get(uid, uid)).with_metadata(json.dumps({"user_id": uid}))
           .with_grants(lk.VideoGrants(room_join=True, room=room)).to_jwt())
    return {"url": url, "token": tok, "room": room}


@app.get("/api/audit/{what}")
def audit_api(what: str):
    from . import audit
    fn = {"traces": lambda: audit.traces(), "ingest": lambda: audit.ingest(ds), "rules": lambda: audit.rules(agent.e), "tools": audit.tools,
          "prompts": lambda: audit.prompts(agent), "memory": lambda: audit.memory(mem, ds), "evals": audit.evals, "answers": audit.answers, "qa": lambda: audit.qa(agent), "context": lambda: audit.context(agent), "architecture": audit.architecture, "health": lambda: audit.health(agent)}.get(what)
    return fn() if fn else {"error": f"unknown audit page {what}"}


@app.post("/api/report/summary")
def report_summary(a: dict):
    """Executive summary for the printable report: model-written from the pinned text only, every ID/number checked against it."""
    from .agent import ID_RE, NUM_RE, call_llm, parse_json
    items = a.get("items", [])[:20]
    facts = "\n".join(f"## {i.get('question', '')}\n{i.get('text', '')}" for i in items)[:9000]
    if not facts.strip():
        return {"bullets": []}
    prompt = ("Write the executive summary of an oil-field operations report: 3-5 short bullets that state the most important findings, risks and what is overdue. Use ONLY the text given; "
              'cite record IDs only if they appear in it; never invent numbers. Return JSON {"bullets":["..."]}.')
    out = parse_json(call_llm([{"role": "system", "content": prompt}, {"role": "user", "content": facts}], 700, json_mode=True, label="report"))
    keep = [b for b in out.get("bullets", []) if all(i in facts for i in ID_RE.findall(b)) and all(n.replace(",", "") in facts.replace(",", "") for n in NUM_RE.findall(b))]
    return {"bullets": keep[:5], "dropped": len(out.get("bullets", [])) - len(keep)}


@app.get("/api/vectors")
def vectors_api():
    from . import audit
    return audit.vectors(agent)


@app.get("/api/vectors/query")
def vectors_query(q: str, k: int = 10):
    from . import audit
    return audit.vquery(agent, q, k)


@app.get("/api/vectors/browse")
def vectors_browse(kind: str = "", q: str = "", limit: int = 30):
    from . import audit
    return audit.vbrowse(agent, kind, q, limit)


@app.get("/api/wiki")
def wiki_index():
    from . import wiki
    return wiki.index(agent.e)


@app.get("/api/wiki/{kind}/{id_}")
def wiki_page(kind: str, id_: str):
    from . import wiki
    return wiki.page(agent.e, kind, id_)


@app.post("/api/wiki/{kind}/{id_}/insights")
def wiki_insights(kind: str, id_: str):
    from . import wiki
    p = wiki.page(agent.e, kind, id_)
    wiki.generate_insights(kind, id_, p["facts"])
    return wiki.page(agent.e, kind, id_)


@app.get("/api/facts")
def facts():
    """Everything users taught the copilot (corrections, rules, notes, claims) incl. revoked/superseded for audit."""
    rows = mem.facts(include_inactive=True)
    agent.e.inspections()   # refresh overlay conflicts
    return {"facts": [{**f, "author_name": ds.user_name.get(f["author"], f["author"])} for f in rows[::-1]],
            "conflicts": agent.e.overlay_conflicts}


@app.post("/api/facts/{fact_id}/revoke")
def revoke(fact_id: int):
    mem.set_status(fact_id, "revoked")
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")
