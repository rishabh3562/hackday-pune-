"""Builds docs/QA_REPORT.md from tests/results/*.json: suite summary, LLM-judge scores, and every real answer next to its expected facts.
  .venv/bin/python tests/qa/report.py   (then ./scripts/build_docs.sh for the PDF)"""
import glob, json, os, time
R = {os.path.basename(p)[:-5]: json.load(open(p)) for p in sorted(glob.glob("tests/results/*.json"))}
md = [f"# QA report\n\nGenerated {time.strftime('%Y-%m-%d %H:%M')} from `tests/results/*.json`. Every real answer is shown next to the expected facts so values can be compared by eye.\n"]
md.append("## Summary\n\n| Suite | Passed | Total | Ran at | What it checks |\n|---|---|---|---|---|")
WHAT = {"golden": "Tools vs the challenge's expected values (no LLM) + SQL cross-check", "extra": "22 extra scenarios vs independent pandas ground truth (LLM routes, code answers)",
        "design-review": "29 stateful scenarios: corrections, recall, privacy, concepts, clarification (10 are core)", "blocks": "Multi-visualization composition (no LLM)", "sql-tool": "Open-ended SQL tool: truth match + safety validator",
        "router-gemini": "Router-only benchmark, Gemini 2.5 Flash (right tool + args)", "router-gemma": "Router-only benchmark, Gemma 4 26B-A4B", "answers": "26 given questions answered by the agent, graded by an LLM judge"}
for k, s in R.items():
    md.append(f"| {k} | {s['passed']} | {s['total']} | {s['ran_at']} | {WHAT.get(k, '')} |")
a = R.get("answers")
if a and any(i.get("judge", {}).get("scores") for i in a["items"]):
    js = [i["judge"] for i in a["items"] if i.get("judge", {}).get("scores")]
    crit = list(js[0]["scores"])
    md.append(f"\n## LLM judge ({a.get('judge_model')})\n\n| Criterion | Average (1-5) |\n|---|---|")
    for c in crit: md.append(f"| {c} | {sum(j['scores'].get(c, 0) for j in js) / len(js):.2f} |")
    verdicts = {v: sum(1 for j in js if j.get("verdict") == v) for v in ("pass", "partial", "fail")}
    md.append(f"\nVerdicts: {verdicts}. Judged answers: {len(js)} of {len(a['items'])}.\n")
def block(i):
    out = [f"### {i['id']}: {i['question']}\n", f"**Expected:** {i['expected']}\n", f"**Actual:** {i['actual']}\n"]
    j = i.get("judge")
    if j and j.get("scores"): out.append(f"**Judge:** {j.get('verdict')} · " + ", ".join(f"{k} {v}" for k, v in j["scores"].items()) + (" · issues: " + "; ".join(j.get("issues", [])) if j.get("issues") else "") + "\n")
    out.append(f"*Deterministic check:* {'pass' if i.get('ok', True) else 'FAIL'}" + (f" · tool `{i['tool']}`" if i.get("tool") else "") + "\n")
    return out
if a:
    md.append("## Given scenarios: expected vs actual\n")
    for i in a["items"]: md += block(i)
if "extra" in R:
    md.append("## Extra scenarios: ground truth vs actual\n")
    for i in R["extra"]["items"]:
        if i.get("actual"): md += block(i)
if "design-review" in R:
    md.append("## Design-review scenarios (stateful dialogues)\n\n| ID | Set | Result | What it tests | Last answer |\n|---|---|---|---|---|")
    for i in R["design-review"]["items"]:
        last = (i.get("answers") or [{}])[-1].get("a", "").replace("\n", " ").replace("|", "/")[:160]
        md.append(f"| {i['id']} | {'core' if i.get('core') else 'extended'} | {'pass' if i['ok'] else 'FAIL'} | {i['desc'].replace('|', '/')} | {last} |")
for k in ("router-gemini", "router-gemma"):
    if k in R: md.append(f"\n## {k}\n\nTool/kind {R[k].get('tool_kind_accuracy')}/{R[k]['total']} · tool + args {R[k].get('tool_args_accuracy')}/{R[k]['total']} (ran {R[k]['ran_at']}).\n")
open("docs/QA_REPORT.md", "w").write("\n".join(md)); print("wrote docs/QA_REPORT.md", len("\n".join(md)), "chars")
