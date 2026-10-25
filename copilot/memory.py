"""SQLite memory: shared facts / corrections (overlay), rule overrides, per-user conversations."""
import json
import sqlite3
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS facts(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, author TEXT,
  kind TEXT,            -- correction | note | rule | claim
  scope_type TEXT,      -- well | well_type | area | fleet
  scope_id TEXT,        -- WELL-0001 | T350 | ...
  inspection_id TEXT, field TEXT, original TEXT, corrected TEXT,
  text TEXT, reason TEXT,
  valid_from TEXT, valid_to TEXT,
  status TEXT           -- confirmed | unconfirmed | conflict
);
CREATE TABLE IF NOT EXISTS convo(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, user_id TEXT, chat_id TEXT,
  role TEXT, text TEXT, entities TEXT, tool TEXT, args TEXT
);
CREATE TABLE IF NOT EXISTS chat_titles(user_id TEXT, chat_id TEXT, title TEXT, PRIMARY KEY(user_id, chat_id));
"""


class Memory:
    def __init__(self, path="memory.db"):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        for col in ("selector TEXT", "op TEXT", "supersedes INTEGER", "role TEXT"):   # migrations for older DB files
            try:
                self.db.execute(f"ALTER TABLE facts ADD COLUMN {col}")
            except sqlite3.OperationalError:
                pass

        try:
            self.db.execute("ALTER TABLE convo ADD COLUMN payload TEXT")   # the answer JSON, so a reopened chat re-renders its visuals
        except sqlite3.OperationalError:
            pass

    def reset(self):
        self.db.executescript("DELETE FROM facts; DELETE FROM convo; DELETE FROM chat_titles;")

    def add_fact(self, **kw):
        kw.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        kw.setdefault("status", "confirmed")
        cols = ",".join(kw)
        self.db.execute(f"INSERT INTO facts({cols}) VALUES({','.join('?' * len(kw))})", list(kw.values()))
        self.db.commit()

    def facts(self, include_inactive=False, **where):
        """Active facts by default; revoked/superseded ones stay in the table as audit history."""
        q = "SELECT * FROM facts"
        conds = [f"{k}=?" for k in where]
        if not include_inactive:
            conds.append("status NOT IN ('revoked','superseded')")
        if conds:
            q += " WHERE " + " AND ".join(conds)
        return [dict(r) for r in self.db.execute(q + " ORDER BY id", list(where.values()))]

    def set_status(self, fact_id, status):
        self.db.execute("UPDATE facts SET status=? WHERE id=?", (status, fact_id))
        self.db.commit()

    def add_correction(self, **kw):
        """Append a correction; a new one on the exact same selector+field supersedes the older active one."""
        for f in self.facts(kind="correction"):
            if f["field"] == kw.get("field") and f.get("selector") == kw.get("selector") and f["inspection_id"] == kw.get("inspection_id"):
                self.set_status(f["id"], "superseded")
                kw["supersedes"] = f["id"]
        self.add_fact(kind="correction", **kw)

    def log(self, user_id, chat_id, role, text, entities=None, tool=None, args=None):
        self.db.execute(
            "INSERT INTO convo(ts,user_id,chat_id,role,text,entities,tool,args) VALUES(?,?,?,?,?,?,?,?)",
            (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), user_id, chat_id, role, text,
             json.dumps(entities or []), tool, json.dumps(args) if args else None))
        self.db.commit()

    def history(self, user_id, exclude_chat=None):
        """Past assistant turns of THIS user only (strict privacy)."""
        rows = self.db.execute(
            "SELECT * FROM convo WHERE user_id=? AND role='assistant' ORDER BY id", (user_id,)).fetchall()
        return [dict(r) for r in rows if r["chat_id"] != exclude_chat]

    def chat_turns(self, user_id, chat_id, n=6):
        rows = self.db.execute(
            "SELECT role,text FROM convo WHERE user_id=? AND chat_id=? ORDER BY id DESC LIMIT ?",
            (user_id, chat_id, n)).fetchall()
        return [dict(r) for r in reversed(rows)]

    # ---- chats (per user; every query is scoped by user_id so one user never sees another's chats) ----
    def save_payload(self, user_id, chat_id, payload):
        """Attach the answer JSON to this chat's latest assistant row."""
        self.db.execute(
            "UPDATE convo SET payload=? WHERE id=(SELECT MAX(id) FROM convo WHERE user_id=? AND chat_id=? AND role='assistant')",
            (json.dumps(payload, default=str), user_id, chat_id))
        self.db.commit()

    def list_chats(self, user_id):
        rows = self.db.execute(
            "SELECT c.chat_id, MAX(c.ts) AS last_ts, MAX(c.id) AS last_id, COUNT(*) AS turns, "
            "(SELECT text FROM convo u WHERE u.user_id=c.user_id AND u.chat_id=c.chat_id AND u.role='user' ORDER BY u.id LIMIT 1) AS first_q, "
            "(SELECT title FROM chat_titles t WHERE t.user_id=c.user_id AND t.chat_id=c.chat_id) AS custom "
            "FROM convo c WHERE c.user_id=? GROUP BY c.chat_id ORDER BY last_id DESC", (user_id,)).fetchall()
        out = []
        for r in rows:
            q = (r["first_q"] or "New chat").strip().replace("\n", " ")
            out.append({"id": r["chat_id"], "title": r["custom"] or (q if len(q) <= 60 else q[:57] + "..."),
                        "last_ts": r["last_ts"], "turns": r["turns"]})
        return out

    def get_chat(self, user_id, chat_id):
        rows = self.db.execute("SELECT id,ts,role,text,tool,args,payload FROM convo WHERE user_id=? AND chat_id=? ORDER BY id",
                               (user_id, chat_id)).fetchall()
        turns = []
        for r in rows:
            t = {"ts": r["ts"], "role": r["role"], "text": r["text"], "tool": r["tool"],
                 "args": json.loads(r["args"]) if r["args"] else None}
            if r["payload"]:
                try: t["payload"] = json.loads(r["payload"])
                except ValueError: pass
            turns.append(t)
        return turns

    def delete_chat(self, user_id, chat_id):
        n = self.db.execute("DELETE FROM convo WHERE user_id=? AND chat_id=?", (user_id, chat_id)).rowcount
        self.db.execute("DELETE FROM chat_titles WHERE user_id=? AND chat_id=?", (user_id, chat_id))
        self.db.commit()
        return n

    def rename_chat(self, user_id, chat_id, title):
        self.db.execute("INSERT OR REPLACE INTO chat_titles(user_id,chat_id,title) VALUES(?,?,?)", (user_id, chat_id, title[:120]))
        self.db.commit()
