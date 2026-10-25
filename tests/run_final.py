"""Final-questions harness. Fresh memory DB, questions processed in order, markdown report for page 2.

  .venv/bin/python tests/run_final.py questions.txt out.md [dataset roots comma-separated]

questions.txt:   one question per line as   User Name: question text
                 a line '--- new chat' starts a new chat for everyone; '# ...' lines are comments."""
import os, sys, time
os.environ.setdefault("COPILOT_CLARIFY", "auto")
os.environ.setdefault("COPILOT_TODAY", "2027-01-15")     # test data: today = 15 Jan 2027
sys.path.insert(0, ".")
if os.path.exists(".env"):
    for l in open(".env"):
        if "=" in l:
            k, v = l.strip().split("=", 1); os.environ.setdefault(k, v)
from copilot.data import Dataset
from copilot.memory import Memory
from copilot.tools import Engine
from copilot.agent import Agent

qfile, outf = sys.argv[1], sys.argv[2]
roots = (sys.argv[3] if len(sys.argv) > 3 else "data/repo/test-data/dataset").split(",")
db = outf + ".memory.db"
if os.path.exists(db):
    os.remove(db)
ds = Dataset(*roots)
agent = Agent(Engine(ds, Memory(db)))
ids = {u["name"].lower(): u["user_id"] for u in ds.users}
chat, n, full = 1, 0, []
md = [f"# Final run\n\nData roots: {', '.join(roots)}. Fresh memory DB. {time.strftime('%Y-%m-%d %H:%M')}\n"]
for line in open(qfile):
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    if line.startswith("---"):
        chat += 1
        continue
    name, q = line.split(":", 1)
    uid = ids.get(name.strip().lower()) or name.strip()
    n += 1
    o = agent.ask(uid, f"final-{chat}-{uid}", q.strip())
    full.append({"n": n, "user": name.strip(), "chat": chat, "question": q.strip(), "answer": {k: v for k, v in o.items() if k in ("text", "visual", "rows", "blocks", "citations", "notes", "plan", "clarify")}})
    md.append(f"## Q{n} ({name.strip()}, chat {chat})\n**{q.strip()}**\n\n{o['text']}\n")
    rows = o.get("rows") or []
    if rows:
        keys = [k for k in rows[0] if k not in ("lat", "lon", "Inspections", "Repairs") or k == "Repairs"][:8]
        md.append(f"*Visual: {o.get('visual')}*\n\n| " + " | ".join(keys) + " |\n|" + "---|" * len(keys))
        for r in rows[:25]:
            md.append("| " + " | ".join(str(r.get(k, ""))[:60].replace("|", "/") for k in keys) + " |")
        if len(rows) > 25:
            md.append(f"\n({len(rows)} rows total)")
    else:
        md.append(f"*Visual: {o.get('visual')}*")
    if o.get("notes"):
        md.append("\n" + "  \n".join(o["notes"]))
    if o.get("citations"):
        md.append("\nEvidence: " + ", ".join(dict.fromkeys(map(str, o["citations"])))[:600])
    md.append("")
    print(f"Q{n} done: {o['plan'].get('tool') or o['plan'].get('kind')}", flush=True)
open(outf, "w").write("\n".join(md))
import json as _j; open(outf.rsplit(".", 1)[0] + ".json", "w").write(_j.dumps(full, default=str, indent=1))
print("wrote", outf)
