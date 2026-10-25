"""Suites save their results as JSON so the Audit > Evaluations page can show them."""
import json, os, time
def save(suite, items, extra=None):
    _history(suite, items)
    os.makedirs(os.path.join(os.path.dirname(__file__), "results"), exist_ok=True)
    with open(os.path.join(os.path.dirname(__file__), "results", f"{suite}.json"), "w") as f:
        json.dump({"suite": suite, "ran_at": time.strftime("%Y-%m-%d %H:%M"), "passed": sum(1 for i in items if i["ok"]), "total": len(items), "items": items, **(extra or {})}, f, indent=1)


def _history(suite, items):
    """Append one line per run so the QA page can show trends and flakiness (results of past runs are never overwritten here)."""
    d = os.path.join(os.path.dirname(__file__), "results"); os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "history.jsonl"), "a") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%d %H:%M"), "suite": suite, "passed": sum(1 for i in items if i["ok"]), "total": len(items), "failed": [i["id"] for i in items if not i["ok"]][:12]}) + "\n")
