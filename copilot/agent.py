"""LLM router (1 call -> strict JSON), deterministic tool execution, deterministic statement handlers, prose call."""
import contextvars
import json
import os
import re
import time

import httpx
import pandas as pd

from .data import TODAY_ISO
from .tools import Engine
from . import blocks, critic
from . import tools2, search, causes, sqltool, ops  # noqa: F401  (importing registers their tools on Engine): F401 registers extra tools

_CUR = contextvars.ContextVar("cur_chat", default=(None, None))     # per-request (user, chat): concurrent chats never share it
MODELS = os.environ.get("COPILOT_MODELS", "poolside/laguna-s-2.1:free,nvidia/nemotron-3-super-120b-a12b:free,google/gemma-4-31b-it:free,google/gemma-4-26b-a4b-it:free,poolside/laguna-xs-2.1:free").split(",")
KEY = os.environ.get("OPEN_ROUTER_API_KEY", "")

TOOLS_DOC = """
TOOLS (pick exactly one for a question):
- well_status{well}                     -> is a well producing now, last inspection, who, reason, planned downtime / shared notes. visual card
- wells_not_producing{area?,well_type?} -> wells not producing right now + reasons. visual table
- timeseries{well,weeks}                -> wellhead vs air temp line chart, marks non-producing. visual line
- spills{area?,well?,wells?,days?,months?,year?,reportable_only?,group_by?}  -> real spills (corrections applied). group_by="area_month" for heatmap. visual table|map|heatmap
- downtime{area?,well?,well_type?,days?,months?,year?,top_n?} -> downtime days per well. visual bar|text
- repair_costs{wells|wells_ref,year?,days?,months?,corrective_only?} -> repair cost per well. Use wells_ref="previous" for "the wells we discussed". visual table
- rca_candidates{area?,equipment,months?} -> wells needing root-cause analysis (equipment e.g. pump_jack, flowline). visual table
- compliance{well?|area?,months?,days?} -> SOP breaches (SR-01 report, SR-02 containment, SR-03 cleanup verification, RC-04 notice response) and pending items. visual table
- spills_over_containment{area,days} -> spills not contained within SOP time limit. visual table
- spill_check{well,date?}               -> was a spill real? shows AI estimate, notes, disagreement. visual card
- repair_summary{group_by=well|area|well_type|equipment|technician|contractor|month, area?,well_type?,year?,months?,days?,maintenance_type=corrective|scheduled?,equipment?,min_count?,top_n?,metric=cost|count?} -> repair counts and cost grouped. "high-failed wells" = group_by well, corrective, months 12, min_count 2
- top_repairs{n,year?,months?,area?,maintenance_type?}  -> most expensive single repairs
- open_repairs_all{area?}               -> repairs currently in progress (planned end after today)
- inspection_gaps{year,min_days,area?}  -> RC-01: wells with more than min_days (default 14) between inspections
- fines{status=open|closed|all,area?}   -> regulator fines
- downtime_trend{area?,well?,year?,months?,freq=month|quarter} -> total downtime days over time. visual line
- mtbf{group_by=well_type|well,area?,months?} -> mean days between corrective repairs
- stale_status{area?}                   -> wells whose recorded_status disagrees with the latest inspection
- spill_breakdown{by=method|area|quarter,area?,months?,year?,reportable_only?,start_year?} -> spill counts by drone/manual, area or quarter
- consecutive_down{min_days,area?}      -> RC-03: wells currently down more than min_days in a row
- repeat_failures{days,year,area?}      -> corrective repairs repeating on same equipment within `days`
- spill_response_summary{months,area?}  -> reportable spills and whether reported on time (SR-01), open fines
- spill_repair_cost{year,area?}         -> cost of repairs triggered by spills, by area
- flowline_tests{year,area?}            -> RC-02: wells missing the annual flowline integrity test
- hot_false_alarms{year,min_temp}       -> hot wellheads (> min_temp C) that were NOT producing, by area
- down_with_recent_repair{days,area?}   -> wells not producing now AND with a corrective repair in the last `days` (ONE call answers 'not producing now and also had a repair')
- newly_stopped{area?}                  -> wells that were producing at the previous inspection but not at the latest
- correction_impact{year}               -> detections removed by corrections
- downtime_cost{months,top_n}           -> top downtime wells with their repair cost and cost per downtime day
- wells_by_cause{concept,area?,months?,year?,equipment?,min_reports?,top_n?} -> wells whose repair reports name a ROOT CAUSE of this kind ('failing due to corrosion / sand / mud / seal wear'). Works on concepts, synonyms and absent words (it says when a word never occurs)
- root_causes{well,equipment?,months?,year?} -> WHY one named well's repairs happened: the root cause quoted from each repair report. Use for 'why did the flowline/pump fail on WELL-X', NOT wells_by_cause
- trace{entity_id}                      -> everything linked to an inspection, repair or well (report, regulator events, notes, corrections)
- sql_query{question} -> LAST RESORT open-ended analysis: the model writes read-only SQL over the corrected data (wells, inspections, maintenance, regulatory_events, human_notes). Use ONLY when none of the tools above can answer; never for questions they cover
- gas_response{since?,well?}            -> OPS-1: gas-odor / H2S operator notes and whether a field response (job or MANUAL inspection) came within the deadline. table Well, Area, Reported at, Response, Hours to response, Deadline, Met/Missed. Pass well for one well (also returns the H2S reading of the response job)
- bypass_audit{}                        -> OPS-2: temporary flowline bypasses (in/out from operator notes) vs MOC memos: Allowed / Expired / Not approved, current and past
- status_conflicts{area?}               -> OPS-3: wells where the latest inspection and a newer shut-in/restart operator note disagree on producing (whole field unless area given)
- cold_weather_check{start?,end?,area?} -> OPS-5: freeze protection: cold inspections on producing wells with no 'Heat trace check' job within 7 days. Use start/end for a month (e.g. December: 2026-12-01..2026-12-31)
- spill_letter_audit{}                  -> the regulator's Nov 2026 letter: reportable spills in Northeast Block 7/8 since 1 Jun 2026 and whether the clean-up report says soil samples were sent to the lab
- recalled_pumps{area?,only_not_producing?} -> (columns include Producing now and Last repaired: for 'which of those pumps/wells are not producing and when last repaired' use this with only_not_producing=true, NOT wells_not_producing) supplier recall HPC-RN-2026-07: Highline RP-175 pumps from recalled lots still in the ground (current pump only, swaps users reported are applied), with install cost. Use area="<user's area>" for 'in my area'
- delay_reasons{year?}                  -> why wells stayed shut in longer than the repair itself (parts, weather, contractor, crew), by area, typical extra days, stacked bar. visual bar
- note_watchlist{days?,top_n?}          -> operator notes about wells that sound/behave wrong with no repair since, ranked by likelihood of needing repair; quotes the notes
- team_info{team}                       -> team lead and number of wells of a team (e.g. 'Northwest Production')
- temperature_by_area{months?}          -> which area runs hotter (wellhead temperature by area, bar)
- data_gap{topic=pressure|production}   -> USE (never sql_query) when the question needs data the dataset does not contain: reservoir pressure map -> topic pressure; 'which well produced the most oil / barrels / volume' -> topic production: says honestly what is missing and the closest proxy
- prioritize{wells_ref="previous"}       -> 'which one would you deal with first / of all the wells we talked about': ranks the wells discussed in this conversation by urgency with reasons
- search_docs{query}                    -> manuals/SOP/report text search. visual text
"""

SYSTEM = f"""You are the routing brain of an oil-field Asset Intelligence Copilot. Today is {TODAY_ISO}. "Right now" = latest inspection.
Areas: {{areas}}.
Reply with ONE JSON object and nothing else.
CLARIFY ({{mode}}): if mode=ask and the request is ambiguous in a way that changes the answer (which area/well/period, which of several meanings, how
widely a change should apply), reply {{"kind":"clarify","question":"<one short question>","options":["<2-4 concrete answers, best guess first>"]}}.
Ask at most once; never ask about style or what the data can decide. References to the earlier conversation ("the wells we discussed", "those wells", "that spill") are resolved by the system: plan the normal tool with "wells_ref":"previous" and NEVER ask which ones. If your previous turn was a clarifying question, the user's reply answers it:
output the full plan for the ORIGINAL request. If mode=auto never ask: pick the best default and add "assumption":"<one line>" to the plan.
Shapes:

A) A QUESTION about data:
{{"kind":"query","tool":"<name>","args":{{...}},"visual":"card|table|line|bar|map|heatmap|text"}}
Only set "visual" explicitly if the user names one (table/chart->bar or line/map/heatmap/card); otherwise omit it.
For "last N months" use months=N; "last 90 days" use days=90; "in 2025" use year=2025; "this year" year=2026; "last 13 weeks" weeks=13; "last 4 years" months=48. "last 12 months" months=12.
Areas must be the full area name (e.g. "Northeast Block 8"). Well ids look like WELL-0001.
{TOOLS_DOC}
A2) ONLY when the question asks for clearly different things that no single tool covers (e.g. one well's status AND a different fleet statistic). If one tool can answer the whole question, including combined conditions (e.g. "not producing now AND had a repair"), use A) with that single tool. Shape: {{"kind":"query","calls":[{{"tool":"...","args":{{}}}},{{"tool":"...","args":{{}}}}],"visual":"..."}} (max 4 calls).
A3) The user only asks to redraw the previous result differently ("show it as a table / bar chart / map"): {{"kind":"rerender","visual":"table|bar|line|map|heatmap|card"}}.

B0) UNDO: {{"kind":"revoke"}} for "undo/revoke my last correction/note".
B) A STATEMENT from the user to remember (not a question). Subtypes:
 1) raw data correction: {{"kind":"correct_raw","well":"WELL-0164","field":"wellhead_temp_c","value":41.0,"date":"2026-10-15","reason":"..."}}
    If it affects MANY inspections (a date range, several wells, an area, a well type, a bias on all readings) add "selector":{{"wells":[..]?,"area":"..."?,"well_type":"T350"?,"date_from":"..."?,"date_to":"..."?,"where":{{"method":"manual"}}?}} and "op":"set|add|mul" (add = shift every matched reading by value, e.g. a sensor reading 2 degrees too high -> op add value -2).
 2) correction of the AI's analysis (spill volume): {{"kind":"correct_ai","well":"WELL-0151","field":"spill_est_volume_bbl","value":5.4,"date":"2026-09-24","reason":"..."}}
 3) rule for a whole well type: {{"kind":"rule","well_type":"T350","rule":"rca_count","value":2,"equipment":"pump_jack","text":"..."}}
 4) fact / FYI / status claim about a well: {{"kind":"note","well":"WELL-0007","text":"...","asserts":"producing|not_producing|planned_shutdown|null","valid_from":"2026-10-17","valid_to":"2026-10-27"}}
    asserts=producing if the user claims it is running / back online; not_producing if it is down / shut in now; planned_shutdown for a future/ongoing planned work note; null otherwise.
    Add "second_hand":true ONLY when the user names someone else as the source ("Nathan told me…", "I heard that…"); a user stating a fact in their own words (even if no work order exists yet) is first-hand, so omit it.
    A statement that equipment was replaced/swapped (e.g. a recalled pump) is a "note" with asserts null.
 5) personal preference about how answers should look, only for this user ("just for me", "whenever you list wells sort by…", "show costs in thousands"): {{"kind":"preference","sort":"area_well"|null,"cost_unit":"thousands"|null,"text":"<their words>"}}
"my area" / "in my area" -> area "@mine" (the system maps it to the user's own area). Dates ISO. If a question has no matching tool, use search_docs.
"""


GCP_PROJECT = os.environ.get("GCP_PROJECT", "omni-505707")
VERTEX_MODEL = os.environ.get("VERTEX_MODEL", "gemini-2.5-flash")
_cred = {}


def _vertex(messages, max_tokens, json_mode):
    import google.auth
    import google.auth.transport.requests as tr
    if "c" not in _cred:
        _cred["c"], _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    c = _cred["c"]
    if not c.valid:
        c.refresh(tr.Request())
    sysm = "\n".join(m["content"] for m in messages if m["role"] == "system")
    contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                for m in messages if m["role"] != "system"]
    gc = {"temperature": 0, "maxOutputTokens": max(max_tokens, 1500)}
    gc["thinkingConfig"] = {"thinkingBudget": 1024} if "pro" in VERTEX_MODEL else {"thinkingBudget": 0}   # Pro models cannot turn thinking off
    if "pro" in VERTEX_MODEL: gc["maxOutputTokens"] = max(max_tokens, 3000)
    if json_mode:
        gc["responseMimeType"] = "application/json"
    r = httpx.post(f"https://aiplatform.googleapis.com/v1/projects/{GCP_PROJECT}/locations/global/publishers/google/models/{VERTEX_MODEL}:generateContent",
                   headers={"Authorization": "Bearer " + c.token},
                   json={"systemInstruction": {"parts": [{"text": sysm}]}, "contents": contents, "generationConfig": gc}, timeout=90)
    j = r.json(); u = j.get("usageMetadata", {})
    _USAGE.update(prompt=u.get("promptTokenCount"), output=(u.get("candidatesTokenCount") or 0) + (u.get("thoughtsTokenCount") or 0), cached=u.get("cachedContentTokenCount") or 0, model=VERTEX_MODEL)
    return j["candidates"][0]["content"]["parts"][0]["text"]


def _gemma(messages, max_tokens, model):
    """Gemma 4 served on Vertex AI (open-model OpenAI-compatible endpoint)."""
    import google.auth
    import google.auth.transport.requests as tr
    if "c" not in _cred:
        _cred["c"], _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    c = _cred["c"]
    if not c.valid:
        c.refresh(tr.Request())
    r = httpx.post(f"https://aiplatform.googleapis.com/v1/projects/{GCP_PROJECT}/locations/global/endpoints/openapi/chat/completions",
                   headers={"Authorization": "Bearer " + c.token},
                   json={"model": model, "messages": messages, "temperature": 0, "max_tokens": max(max_tokens, 1500)}, timeout=120)
    j = r.json(); u = j.get("usage", {})
    _USAGE.update(prompt=u.get("prompt_tokens"), output=u.get("completion_tokens"), cached=0, model=model)
    return j["choices"][0]["message"]["content"]


STATS = {"calls": 0, "in_chars": 0, "out_chars": 0, "backend": None}


_USAGE = {}
CALLS = []      # every model call of this process: label, model, REAL token counts from the API, and the character split of the prompt


def call_llm(messages, max_tokens=900, temperature=0.0, json_mode=False, label="llm"):
    _USAGE.clear(); t0 = time.time()
    out = _call_llm(messages, max_tokens, temperature, json_mode)
    chars = [(m["role"], len(m["content"])) for m in messages]
    STATS["calls"] += 1; STATS["in_chars"] += sum(c for _, c in chars); STATS["out_chars"] += len(out)
    CALLS.append({"label": label, "model": _USAGE.get("model") or os.environ.get("VERTEX_MODEL", "gemini-2.5-flash"), "prompt_tokens": _USAGE.get("prompt") or sum(c for _, c in chars) // 4,
                  "output_tokens": _USAGE.get("output") or len(out) // 4, "cached_tokens": _USAGE.get("cached") or 0, "ms": int((time.time() - t0) * 1000), "chars": chars, "exact": _USAGE.get("prompt") is not None})
    return out


def _call_llm(messages, max_tokens=900, temperature=0.0, json_mode=False):
    last = None
    if os.environ.get("COPILOT_BACKEND") == "gemma":
        for _ in range(3):
            try:
                return _gemma(messages, max_tokens, os.environ.get("GEMMA_MODEL", "google/gemma-4-26b-a4b-it-maas"))
            except Exception as ex:  # noqa: BLE001
                last = ex
        raise RuntimeError(f"Gemma unavailable: {last}")
    if os.environ.get("USE_VERTEX", "1") == "1":
        for _ in range(2):
            try:
                return _vertex(messages, max_tokens, json_mode)
            except Exception as ex:  # noqa: BLE001
                last = ex
    for model in MODELS:
        for attempt in range(2):
            try:
                r = httpx.post("https://openrouter.ai/api/v1/chat/completions",
                               headers={"Authorization": f"Bearer {KEY}"},
                               json={"model": model, "messages": messages, "temperature": temperature,
                                     "max_tokens": max(max_tokens, 2500)}, timeout=90)
                j = r.json()
                if "choices" in j and j["choices"][0]["message"].get("content"):
                    u = j.get("usage", {}); _USAGE.update(prompt=u.get("prompt_tokens"), output=u.get("completion_tokens"), cached=0, model=model)
                    return j["choices"][0]["message"]["content"]
                last = j
            except Exception as ex:  # noqa: BLE001
                last = ex
            time.sleep(1)
    raise RuntimeError(f"LLM unavailable: {last}")


def parse_json(txt):
    txt = re.sub(r"```(?:json)?", "", txt)
    s, e = txt.find("{"), txt.rfind("}")
    return json.loads(txt[s:e + 1])


ID_RE = re.compile(r"\b(?:WELL-\d{4}|INS-\d{4}-\d{4}|MNT-\d{4}-\d{3}|CTX-\d{4}-\d{3}|REG-\d{4}-\d{3}|OM-T\d+|SR-\d\d|RC-\d\d)\b")
NUM_RE = re.compile(r"(?<![\w.-])\d[\d,]*\.\d+|(?<![\w.-])\d{3,}(?:,\d{3})*(?![\w-])")


def clean(t):
    return re.sub(r"【[^】]*】", "", t).strip()


def ungrounded(text, res, facts_json):
    """Claims in the prose that the tool result does not support: unknown IDs, numbers, or missing wells."""
    facts = facts_json + json.dumps(res.get("citations", []), default=str)
    bad = [i for i in set(ID_RE.findall(text)) if i not in facts]
    plain = re.sub(r"\d{4}-\d\d-\d\d", "", ID_RE.sub("", text))
    for n in NUM_RE.findall(plain):
        n2 = n.replace(",", "")
        if n not in facts and n2 not in facts and not any(n2 in f for f in re.findall(r"\d+\.?\d*", facts)):
            if re.fullmatch(r"(19|20)\d\d", n2):
                continue
            bad.append(n)
    rows = res.get("rows") or []
    if 0 < len(rows) <= 15 and all("Well" in r for r in rows) and not res.get("no_missing"):
        bad += [f"missing {r['Well']}" for r in rows if r["Well"] not in text]
    return bad


CONTRA = re.compile(r"(?P<id>WELL-\d{4})\W[^.\n]{0,90}?\b(?:does not|doesn't|do not|don't|not)\s+(?:need|needs|qualify|qualifies|meet|meets|require|requires|appear|included|listed)\b|(?:excluding|except|excludes?|excluded)\W[^.\n]{0,40}(?P<id2>WELL-\d{4})", re.I)


def contradicts(text, res):
    """Prose that says a listed row does not qualify / is excluded (the table says otherwise)."""
    ids = {r["Well"] for r in (res.get("rows") or []) if isinstance(r, dict) and "Well" in r}
    return [m.group("id") or m.group("id2") for m in CONTRA.finditer(text) if (m.group("id") or m.group("id2")) in ids] if ids else []


def lead_line(res):
    """A deterministic one-line list of the wells in the result, so the written answer can never drop or flip one."""
    rows = res.get("rows") or []
    if len(rows) < 2 or not all(isinstance(r, dict) and "Well" in r for r in rows) or len(rows) > 15: return ""
    return "Wells: " + ", ".join(dict.fromkeys(r["Well"] for r in rows)) + "."


def template_answer(res):
    rows = res.get("rows") or []
    head = f"{len(rows)} result(s)." if rows else "No matching records."
    if rows and "Well" in rows[0]:
        head += " Wells: " + ", ".join(dict.fromkeys(str(r["Well"]) for r in rows[:20])) + "."
    return " ".join([head] + list(res.get("notes", []))[:3])


WRITER_PROMPT = ("Answer the operator's question using ONLY the JSON facts. Be concise (3-8 sentences), exact numbers, cite record IDs "
          "in parentheses (inspection/maintenance/note/event IDs), refer to wells by ID and people/areas by name. "
          "If a reason is missing say 'no recorded reason' and suggest a field check; never invent causes. "
          "Every row in rows satisfies the question's filter: list them all and never say a listed row does not qualify. Mention corrections, out-of-date recorded status, and disagreements when present in the JSON. "
          "For well_status: if shared_facts contain a planned shutdown, state the dates (valid_from/valid_to), who said it and its status first. Otherwise say producing yes/no, last inspection ID/date/inspector, temperature rise vs threshold, any note or open repair explaining it, whether recorded_status is out of date. "
          "Do not describe the chart; the UI draws it. Plain text only: no ASCII charts, no 【】 brackets, no JSON field names; cite IDs like (INS-0001-0203).")



def build_context(calls, out, agent):
    """What this answer cost in context: real token counts per model call, the prompt split by part, rows returned vs sent, guard outcome, share of the dataset."""
    rows = []
    for c in calls:
        tot = max(1, sum(n for _, n in c["chars"])); k = c["prompt_tokens"] / tot; parts = {}
        for idx, (role, n) in enumerate(c["chars"]):
            if c["label"].startswith("router"):
                nm = "instructions + tools (fixed)" if role == "system" else ("your question" if idx == len(c["chars"]) - 1 and role == "user" else "conversation so far")
            elif c["label"].startswith("writer"):
                nm = "writer instructions (fixed)" if role == "system" else "tool result (facts)" if idx == 1 else "retry feedback"
            else: nm = role
            parts[nm] = parts.get(nm, 0) + n * k
        rows.append({"label": c["label"], "model": c["model"], "prompt_tokens": c["prompt_tokens"], "output_tokens": c["output_tokens"], "cached_tokens": c["cached_tokens"], "ms": c["ms"], "exact": c["exact"],
                     "parts": [{"name": n, "tokens": int(round(v))} for n, v in parts.items()]})
    meta = out.get("context_meta") or next((p.get("context_meta") for p in out.get("parts", []) if p.get("context_meta")), {}) or {}
    total = sum(r["prompt_tokens"] + r["output_tokens"] for r in rows)
    return {"calls": rows, "prompt_tokens": sum(r["prompt_tokens"] for r in rows), "output_tokens": sum(r["output_tokens"] for r in rows), "total_tokens": total, "cached_tokens": sum(r["cached_tokens"] for r in rows),
            "tool_ms": sum(p.get("tool_ms", 0) for p in out.get("parts", [])) if out.get("parts") else out.get("tool_ms"),
            "rows_returned": meta.get("rows_returned"), "rows_sent": meta.get("rows_sent"), "facts_chars": meta.get("facts_chars"), "guard": meta.get("guard"), "mode": agent.mode,
            "dataset_tokens": agent.e.ds.data_tokens, "share_of_dataset_pct": round(100 * sum(r["prompt_tokens"] for r in rows) / max(1, agent.e.ds.data_tokens), 4)}



def normalize_plan(plan):
    """Planners sometimes return the tool name as the kind ({"kind":"search_docs","query":..}) or put arguments at the top level: repair the shape deterministically."""
    if not isinstance(plan, dict): return plan
    tools = set(re.findall(r"^- (\w+)\{", TOOLS_DOC, re.M))
    if plan.get("kind") in tools:
        t = plan.pop("kind"); vis = plan.pop("visual", None)
        args = plan.pop("args", None) or {k: v for k, v in plan.items() if k not in ("tool", "kind")}
        plan = {"kind": "query", "tool": t, "args": args, **({"visual": vis} if vis else {})}
    elif plan.get("tool") and not plan.get("kind"):
        plan["kind"] = "query"
    return plan


RECALL_RE = re.compile(r"\b(we discussed|discussed (?:yesterday|earlier|before|last)|those wells|the wells we|same wells|earlier answer|previous answer|that spill|those spills)\b", re.I)


_MODE = contextvars.ContextVar("clarify_mode", default=None)      # per-request override, isolated between concurrent requests


class Agent:

    @property
    def mode(self):
        """ask = may ask the user a clarifying question; auto = never ask, state the assumption. A per-request override wins over the server default."""
        return _MODE.get() or self._mode

    @mode.setter
    def mode(self, v):
        self._mode = v

    def __init__(self, engine: Engine):
        self.e = engine
        self.areas = ", ".join(a["name"] for a in engine.ds.areas)
        self._mode = os.environ.get("COPILOT_CLARIFY", "ask")   # server default; a request may override it (see ask(..., mode=))
        self.pending = {}   # (user, chat) -> action waiting for a yes/no confirmation
        self.last = {}   # (user, chat) -> last result, for "show it as a bar chart" without re-querying

    # ---- entry ----
    def ask(self, user_id, chat_id, text, mode=None):
        tok = _MODE.set(mode) if mode in ("ask", "auto") else None
        try:
            return self._ask(user_id, chat_id, text)
        finally:
            if tok is not None: _MODE.reset(tok)

    def _ask(self, user_id, chat_id, text):
        e = self.e
        who = e.uname(user_id)
        _CUR.set((user_id, chat_id))
        t0, s0, c0 = time.time(), dict(STATS), len(CALLS)
        pend = self.pending.get((user_id, chat_id))
        if pend and re.fullmatch(r"\s*(yes|y|apply|confirm|ok|okay|go ahead|do it|apply to all( \d+)?)[.! ]*", text.lower()):
            self.pending.pop((user_id, chat_id))
            e.mem.log(user_id, chat_id, "user", text)
            out = self.correct_many(pend["plan"], pend["who"], pend["text"], confirmed=True)
            e.mem.log(user_id, chat_id, "assistant", out["text"], [], "correct_many")
            out["plan"] = {"kind": "confirm"}
            return out
        if pend and re.fullmatch(r"\s*(no|n|cancel|stop|never ?mind|don't|narrow it)[.! ]*", text.lower()):
            self.pending.pop((user_id, chat_id))
            e.mem.log(user_id, chat_id, "user", text)
            out = {"text": "Cancelled, nothing was changed. Tell me the narrower scope (wells, area, dates) when ready.", "visual": "text", "rows": [], "citations": [], "plan": {"kind": "cancel"}}
            e.mem.log(user_id, chat_id, "assistant", out["text"], [], "cancel")
            return out
        turns = e.mem.chat_turns(user_id, chat_id, 4)
        msgs = [{"role": "system", "content": SYSTEM.replace("{areas}", self.areas).replace("{mode}", self.mode)}]
        for t in turns:
            msgs.append({"role": t["role"], "content": t["text"][:400]})
        msgs.append({"role": "user", "content": f"[user: {who}] {text}"})
        plan, ex = None, None
        for _ in range(3):
            try:
                plan = parse_json(call_llm(msgs, json_mode=True, label="router"))
                break
            except Exception as e_:  # noqa: BLE001
                ex = e_
        plan = normalize_plan(plan)
        if plan and plan.get("kind") not in ("query", "rerender", "correct_raw", "correct_ai", "rule", "note", "preference", "revoke", "clarify"):
            try:
                plan = parse_json(call_llm(msgs + [{"role": "assistant", "content": json.dumps(plan)}, {"role": "user", "content":
                        'That is not a valid plan. Reply again with one JSON object whose "kind" is one of query, rerender, correct_raw, correct_ai, rule, note, preference, revoke, clarify.'}], json_mode=True, label="router-retry"))
            except Exception:  # noqa: BLE001
                pass
        if plan and plan.get("kind") == "clarify" and RECALL_RE.search(text):   # the planner cannot know the earlier wells: its options would be invented
            try:
                plan = normalize_plan(parse_json(call_llm(msgs + [{"role": "assistant", "content": json.dumps(plan)}, {"role": "user", "content":
                        'Do not ask. This refers to the earlier conversation, which the system resolves. Output the normal query plan for the original request with "wells_ref":"previous" (or the matching tool with its other arguments).'}], json_mode=True, label="router-retry")))
            except Exception:  # noqa: BLE001
                pass
        asked = plan.get("question") if plan and plan.get("kind") == "clarify" else None
        if plan and plan.get("kind") == "clarify" and self.mode == "auto":   # nobody to answer: force a best-guess plan
            try:
                plan = parse_json(call_llm(msgs + [{"role": "assistant", "content": json.dumps(plan)}, {"role": "user", "content":
                        "Mode is auto, do not ask. Output the full plan for the original request with your best default and an \"assumption\" line."}], json_mode=True, label="router-retry"))
            except Exception:  # noqa: BLE001
                pass
            plan = normalize_plan(plan)
            if asked and isinstance(plan, dict) and not plan.get("assumption"):
                plan["assumption"] = f"your request was open-ended, so I used the most likely reading (I would otherwise have asked: {asked})"
        if plan is None:
            return {"text": f"Sorry, I could not interpret that ({ex}).", "visual": "text", "rows": [], "citations": []}
        e.mem.log(user_id, chat_id, "user", text)
        try:
            out = self.dispatch(plan, user_id, who, text, chat_id)
            if plan.get("assumption") and self.mode == "auto":
                out["notes"] = list(out.get("notes", [])) + [f"Assumed: {plan['assumption']}"]
        except Exception as ex:  # noqa: BLE001
            out = {"text": f"I could not complete that: {ex}", "visual": "text", "rows": [], "citations": []}
        ents = sorted({r.get("Well") or r.get("well") for r in out.get("rows", []) if isinstance(r, dict) and (r.get("Well") or r.get("well"))})
        e.mem.log(user_id, chat_id, "assistant", out["text"], ents, plan.get("tool") or plan.get("kind"), plan.get("args"))
        must = [n for n in out.get("notes", []) if re.match(r"(Assumed:|No conversation of yours|I used |No record mentions|Showing the closest)", n) and n not in out.get("text", "")]
        if must and out.get("visual") != "clarify":      # an assumption or a fallback must be said in the answer itself, not only in a side note
            out["text"] = (out.get("text") or "") + "\n" + " ".join(must)
        out["plan"] = plan
        out["context"] = build_context(CALLS[c0:], out, self)
        try:
            with open(os.environ.get("TRACE_FILE", "traces.jsonl"), "a") as f:
                f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "user": user_id, "chat": chat_id, "question": text,
                                    "plan": plan, "visual": out.get("visual"), "blocks": [b["type"] for b in out.get("blocks", [])],
                                    "citations": out.get("citations", [])[:50], "notes": out.get("notes", [])[:6], "answer": out.get("text"),
                                    "ms": int((time.time() - t0) * 1000), "llm_calls": STATS["calls"] - s0["calls"], "mode": self.mode,
                                    "approx_tokens": out["context"]["total_tokens"], "context": out["context"]}, default=str) + "\n")
        except OSError:
            pass
        return out

    def clarify(self, question, options):
        """A question back to the user: 2-4 options plus free text. The next message is read as its answer."""
        if self.mode == "auto":
            return {"text": "I need a bit more detail: " + question, "visual": "text", "rows": [], "citations": []}
        opts = [str(o) for o in options][:4]
        return {"text": question + ("\n" + "\n".join(f"{i}. {o}" for i, o in enumerate(opts, 1)) if opts else "") + "\nOr tell me in your own words.",
                "visual": "clarify", "options": opts, "allow_free_text": True, "rows": [], "citations": []}

    # ---- dispatch ----
    def dispatch(self, plan, user_id, who, text, chat_id=None):
        k = plan.get("kind")
        if k == "clarify":
            return self.clarify(plan.get("question") or "Can you tell me a bit more?", plan.get("options") or [])
        if k == "rerender":
            prev = self.last.get((user_id, chat_id))
            if not prev:
                return {"text": "There is no earlier result in this chat to redraw. Ask a question first.", "visual": "text", "rows": [], "citations": []}
            out = {**prev, "visual": plan.get("visual") or prev["visual"]}
            out["text"] = f"Same data, shown as a {out['visual']} (no new query)."
            out["blocks"] = blocks.rerender(prev, out["visual"])
            return out
        if k == "query":
            return self.query(plan, user_id, text, chat_id)
        if k == "revoke":
            return self.revoke(plan, who)
        if k == "correct_raw":
            return self.correct(plan, who, text, ai=False)
        if k == "correct_ai":
            return self.correct(plan, who, text, ai=True)
        if k == "rule":
            return self.rule(plan, who)
        if k == "note":
            return self.note(plan, who, text)
        if k == "preference":
            return self.preference(plan, user_id, who, text)
        return {"text": "I did not understand that.", "visual": "text", "rows": [], "citations": []}

    def query(self, plan, user_id, text, chat_id=None):
        calls = plan.get("calls") or [{"tool": plan.get("tool"), "args": plan.get("args")}]
        results = []
        for c in calls[:4]:
            _t = time.time()
            r = self.execute(c.get("tool"), dict(c.get("args") or {}), c.get("visual") or plan.get("visual"), user_id, text)
            r["tool_ms"] = int((time.time() - _t) * 1000)
            if "text" in r and not r.get("rows") and r.get("visual") in ("text", "clarify") and len(calls) == 1:
                return r  # refusal / clarification
            r["tool"] = c.get("tool")
            results.append(r)
        for r in results:
            r["blocks"] = blocks.build(self.e, r["tool"], r)
        if len(results) == 1:
            res = results[0]
            res["text"] = self.compose(text, res, res["tool"])
        else:
            res = {**{k: v for k, v in results[0].items() if k not in ("text", "notes", "citations", "args", "tool")},
                   "visual": results[0]["visual"], "rows": results[0]["rows"], "parts": results,
                   "blocks": [b for r in results for b in r["blocks"]],
                   "citations": [c for r in results for c in r.get("citations", [])],
                   "notes": [n for r in results for n in r.get("notes", [])], "args": results[0].get("args")}
            res["text"] = self.compose(text, {**res, "rows": [], "parts": [
                {k: r.get(k) for k in ("tool", "rows", "notes", "citations")} for r in results]}, "multi")
        if chat_id:
            self.last[(user_id, chat_id)] = res
        return res

    def resolve_prior(self, user_id, text):
        """'The wells we discussed (yesterday / last month / in April)': this user's own earlier answers only, matched by
        time window and by how many wells they said ('three wells'). Falls back to the latest match and says so."""
        import datetime as dt
        e = self.e
        hist = [h for h in e.mem.history(user_id) if json.loads(h["entities"] or "[]")]
        if not hist:
            return None, ("I have no earlier conversation with you that I can use for that, so I don't know which wells you mean. "
                          "Which wells should I look at?"), []
        t = text.lower()
        nums = {"two": 2, "three": 3, "four": 4, "five": 5, "2": 2, "3": 3, "4": 4, "5": 5}
        m = re.search(r"\b(two|three|four|five|[2-5])\s+(?:wells|of)", t)
        want = nums.get(m.group(1)) if m else None
        cand = [h for h in hist if len(json.loads(h["entities"])) == want] if want else hist
        if not cand:
            return None, ("I have no earlier conversation with you about that set of wells, so I don't know which wells you mean. "
                          "Which wells should I look at?"), []
        now = dt.datetime.utcnow()
        win, label = None, None
        months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
        if "yesterday" in t:
            win, label = (now - dt.timedelta(days=2), now - dt.timedelta(hours=0)), "yesterday"
        elif "last week" in t:
            win, label = (now - dt.timedelta(days=14), now), "last week"
        elif "last month" in t:
            win, label = (now - dt.timedelta(days=62), now), "last month"
        else:
            mm = next((i for i, n in enumerate(months, 1) if re.search(rf"\b(in|during|last)?\s*{n}\b", t)), None)
            if mm:
                y = now.year if mm <= now.month else now.year - 1
                win, label = (dt.datetime(y, mm, 1), dt.datetime(y + (mm == 12), mm % 12 + 1, 1)), months[mm - 1].title()
        notes = []
        if win:
            inwin = [h for h in cand if win[0] <= dt.datetime.strptime(h["ts"], "%Y-%m-%dT%H:%M:%SZ") <= win[1]]
            if inwin:
                cand = inwin
            else:
                notes.append(f"No conversation of yours matched '{label}', so I used your most recent matching one ({cand[-1]['ts'][:10]}).")
        sets = []
        for h in cand:
            s_ = json.loads(h["entities"])
            if s_ not in [x[0] for x in sets]:
                sets.append((s_, h["ts"][:10], h.get("tool")))
        pick = sets[-1]
        if len(sets) > 1 and self.mode == "ask":
            opts = [f"{', '.join(x[0])} ({x[1]})" for x in sets[::-1][:3]]
            return None, None, {"clarify": ("You looked at more than one set of wells. Which do you mean?", opts)}
        if len(sets) > 1:
            notes.append("I used " + ", ".join(pick[0]) + f" (from {pick[1]}). Other sets you looked at: " +
                         "; ".join(f"{', '.join(x[0])} ({x[1]})" for x in sets[-4:-1]) + ". Tell me if you meant one of those.")
        return pick[0], None, notes

    def my_area(self, user_id):
        """The area a user's team works in (the area most of its wells are in)."""
        e = self.e
        team = next((u["team_id"] for u in e.ds.users if u["user_id"] == user_id), None)
        w = e.ds.w[e.ds.w.team_id == team]
        return e.ds.area_name[w.area_id.mode().iloc[0]] if len(w) else None

    def execute(self, tool, args, vis, user_id, text):
        e = self.e
        extra_notes = []
        if tool == "prioritize" and not args.get("wells"):      # every well shown to this user in THIS chat so far
            uid, cid = _CUR.get()
            rows = e.mem.db.execute("SELECT entities FROM convo WHERE user_id=? AND chat_id=? AND role='assistant'", (uid, cid)).fetchall()
            args["wells"] = sorted({w for r in rows for w in json.loads(r[0] or "[]")})
            args.pop("wells_ref", None)
            if not args["wells"]:
                return {"text": "No wells have come up in this conversation yet, so there is nothing to rank. Which wells should I compare?", "visual": "text", "rows": [], "citations": []}
        if tool == "repair_costs" and (args.get("wells_ref") or not args.get("wells")):
            ids, msg, extra_notes = self.resolve_prior(user_id, text)
            if isinstance(extra_notes, dict):
                return self.clarify(*extra_notes["clarify"])
            if msg:
                return {"text": msg, "visual": "text", "rows": [], "citations": []}
            args["wells"] = ids
        args.pop("wells_ref", None)
        if str(args.get("area", "")) == "@mine":
            args["area"] = self.my_area(user_id)
        if args.pop("corrective_only", False) and tool in ("repair_summary", "top_repairs"):
            args["maintenance_type"] = "corrective"
        fn = getattr(e, tool, None)
        if fn is None:
            raise ValueError(f"unknown tool {tool}")
        import inspect
        ok = set(inspect.signature(fn).parameters)
        args = {k: v for k, v in args.items() if k in ok and v not in (None, "")}
        if str(args.get("area", "")).strip().lower() in {"all", "all areas", "fleet", "field", "everywhere", "any", "none", "whole field", "entire field"}:
            args.pop("area")                       # "all" means no area filter, not an area called "all"
        if args.get("area"):
            try:
                args["area"] = e.resolve_area(args["area"])
            except ValueError:
                names = [a["name"] for a in e.ds.areas]
                if self.mode == "ask":
                    return self.clarify(f"I don't know the area '{args['area']}'. Which one do you mean?", names[:4])
                raise
        for key in ("area",):
            if key in args and tool != "wells_not_producing":
                args[key] = e.resolve_area(args[key]) if args[key] else None
        if str(args.get("area", "")) == "@mine":
            args["area"] = self.my_area(user_id)
        wid = args.get("well")
        if wid and wid not in e.ds.w.index:
            import difflib
            close = difflib.get_close_matches(wid, list(e.ds.w.index), n=3, cutoff=0.6)
            if close and self.mode == "ask":
                return self.clarify(f"{wid} is not in the data. Did you mean one of these?", close)
            return {"text": f"{wid} is not in the data" + (f" (closest: {', '.join(close)})." if close else "."), "visual": "text", "rows": [], "citations": []}
        res = fn(**args)
        if res.get("error"):
            return {"text": res["error"], "visual": "text", "rows": [], "citations": []}
        if res.get("suggestions"):   # nothing matched literally: offer grounded alternatives instead of a dead end
            sug = res["suggestions"]
            if self.mode == "ask":
                opts = [f"{x['cause']} ({x['reports']} reports, {x['wells']} wells)" for x in sug] + (["Show all of these"] if len(sug) > 1 else [])
                return self.clarify(f"No record mentions '{res['concept']}'. The closest causes in the data ({res['window']}) are below. Which should I use?", opts)
            if res.get("rows"):            # auto mode: the related matches are shown, with the assumption stated
                res.setdefault("notes", []).insert(0, f"No record mentions '{res['concept']}'. Showing the closest causes in the data instead.")
                sug = None
        if res.get("suggestions") and self.mode != "ask" and not res.get("rows"):
            assumed = sug[0]["cause"]
            res2 = self.e.wells_by_cause(assumed, **{k: v for k, v in args.items() if k != "concept"})
            res2["notes"] = [f"No record mentions '{res['concept']}'. Assumed the closest cause: {assumed} ({sug[0]['reports']} reports, {sug[0]['wells']} wells)."] + list(res2.get("notes", []))
            res = res2
        res["notes"] = list(res.get("notes", [])) + extra_notes
        if vis in ("card", "table", "line", "bar", "map", "heatmap") and tool not in ("trace", "wells_by_cause"):
            res["visual"] = vis
        res["args"] = args
        return self.apply_prefs(res, user_id, e.ds.user_name.get(user_id, user_id))

    def compose(self, question, res, tool):
        if os.environ.get("NO_WRITER") == "1":   # router-only benchmark
            return template_answer(res)
        if tool in ops.DET and (res.get("rows") or []):     # long audit tables: deterministic text, every number straight from the tool
            return ops.summary(tool, res)
        slim = {k: res[k] for k in ("rows", "parts", "notes", "pending", "total_bbl", "count", "citations") if k in res}
        if len(slim.get("rows", [])) > 30:
            slim["rows_total"] = len(slim["rows"])
            slim["rows"] = slim["rows"][:30]
        s = json.dumps(slim, default=str)[:7000]
        res["context_meta"] = {"rows_returned": len(res.get("rows") or []), "rows_sent": len(slim.get("rows", [])), "facts_chars": len(s), "facts_cap_chars": 7000, "guard": "passed first time"}
        prompt = WRITER_PROMPT
        base = [{"role": "system", "content": prompt},
                {"role": "user", "content": f"Question: {question}\nTool: {tool}\nFacts JSON: {s}"}]
        try:
            t = clean(call_llm(base, 700, label="writer"))
            bad = ungrounded(t, res, s + " " + question + json.dumps(res.get("args"), default=str)) + [f"contradicts the table about {w}" for w in contradicts(t, res)]
            if bad:
                t = clean(call_llm(base + [{"role": "assistant", "content": t}, {"role": "user", "content":
                      f"Rewrite. These are not supported by the facts: {bad}. Mention every row/ID that matters and use only facts given."}], 700, label="writer-retry"))
                bad = ungrounded(t, res, s + " " + question + json.dumps(res.get("args"), default=str)) + [f"contradicts the table about {w}" for w in contradicts(t, res)]
            if res.get("context_meta") and len([c for c in CALLS[-3:] if c["label"] == "writer-retry"]): res["context_meta"]["guard"] = "regenerated once"
            if not bad and os.environ.get("CRITIC", "on") == "on" and tool not in critic.SKIP_TOOLS:     # semantic review by a stronger model
                ok, problems = critic.review(question, s, t)
                if res.get("context_meta"): res["context_meta"]["critic"] = "ok" if ok else f"flagged: {'; '.join(problems)[:160]}"
                if not ok:
                    t2 = clean(call_llm(base + [{"role": "assistant", "content": t}, {"role": "user", "content": "A reviewer found problems. Rewrite using only the facts and fix them: " + "; ".join(problems)}], 700, label="writer-retry"))
                    if not ungrounded(t2, res, s + " " + question) and not contradicts(t2, res): t = t2
            if not bad:
                t = lead_line(res) + "\n" + t if lead_line(res) and lead_line(res).split(": ", 1)[1].split(", ")[0] not in t.split("\n")[0] else t
                miss = [n for n in res.get("notes", []) if (ID_RE.findall(n) and not any(i in t for i in ID_RE.findall(n))) or any(x not in t for x in re.findall(r"\d+\.\d+", n))]   # notes whose IDs or decimal figures the prose left out
                return t + ("\n" + " ".join(miss[:3]) if miss else "")
            res.setdefault("notes", []).append(f"(Summary replaced by a template: unsupported claims {bad[:4]}.)")
            if res.get("context_meta"): res["context_meta"]["guard"] = "template fallback"
        except Exception:  # noqa: BLE001
            pass
        return template_answer(res)

    # ---- statements ----
    def _find_inspection(self, well, date, need_spill=False):
        i = self.e.ds.i[self.e.ds.i.asset_id == well]
        if need_spill:
            i = i[i.spill_detected]
        if i.empty:
            return None
        if date:
            d = pd.Timestamp(date, tz="UTC")
            return i.iloc[(i.ts - d).abs().argsort()].iloc[0]
        return i.sort_values("ts").iloc[-1]

    def correct(self, p, who, text, ai):
        e = self.e
        if p.get("selector") or isinstance(p.get("wells"), list) or not p.get("well"):   # no single well named: it is a multi-row change
            return self.correct_many(p, who, text)
        well, field, val = p["well"], p["field"], p["value"]
        r = self._find_inspection(well, p.get("date"), need_spill=ai)
        if r is None:
            return {"text": f"I could not find a matching inspection for {well}.", "visual": "text", "rows": [], "citations": []}
        orig = r["wellhead_temp_c"] if field == "wellhead_temp_c" else r["spill_est_volume_bbl"]
        e.mem.add_fact(kind="correction", author=who, scope_type="well", scope_id=well, inspection_id=r["inspection_id"],
                       field=field, original=str(orig), corrected=str(val), reason=p.get("reason") or text, text=text)
        lines = [f"Recorded {who}'s correction on {r['inspection_id']} ({r['ts'].date()}): {field} {orig} -> {val}. "
                 f"The original value is kept and the correction applies to every user from now on. Reason: {p.get('reason') or text}"]
        extra = {}
        if not ai:
            st = e.well_status(well)["rows"][0]
            lines.append(f"With the corrected reading, the wellhead is {st['delta_c']} °C above air (limit {st['threshold_c']} °C), so {well} "
                         f"{'IS' if st['producing'] else 'is NOT'} producing oil.")
            if r["notes"]:
                lines.append(f"Note: the same inspection has the inspector note \"{r['notes']}\" which may disagree with this correction. "
                             f"Can you confirm?")
            extra = {"visual": "card", "rows": [st]}
        else:
            c = e.compliance(well=well, days=90)
            vol = float(val)
            klass = e.spill_class(vol)
            lines.append(f"At {vol} bbl the spill is now '{klass}'. (AI estimate was {orig} bbl, kept for reference.)")
            for it in c["rows"] + c["pending"]:
                if it["Spill"] == r["inspection_id"] or it["Protocol"] in ("SR-01", "SR-02", "SR-03"):
                    lines.append(f"- {it['Protocol']}: {it['Finding']} (evidence {it['Evidence']})")
            m = e.ds.m[e.ds.m.triggered_by_inspection_id == r["inspection_id"]]
            for x in m.itertuples():
                rep = e.ds.reports.get(x.maintenance_id, "")
                if "moderate" in rep.lower() and klass in ("reportable", "major"):
                    lines.append(f"- Repair report {x.maintenance_id} classed this spill 'moderate' with no reporting duty; that was based on the old estimate and no longer holds.")
            extra = {"visual": "table", "rows": c["rows"] + c["pending"]}
        return {"text": "\n".join(lines), "citations": [r["inspection_id"]], **({"visual": "text", "rows": []} | extra)}

    def correct_many(self, p, who, text, confirmed=False):
        """One feedback -> many rows. The selector is stored and evaluated when read; nothing is overwritten."""
        e = self.e
        sel = dict(p.get("selector") or {})
        for k in ("wells", "well_type", "area", "date_from", "date_to", "where"):
            if p.get(k) and k not in sel:
                sel[k] = p[k]
        if isinstance(sel.get("wells"), str):
            sel["wells"] = [sel["wells"]]
        if sel.get("area"):
            sel["area"] = e.resolve_area(sel["area"])
        fact = {"selector": json.dumps(sel), "inspection_id": None}
        mask = e._selector_mask(e.ds.i, fact)
        n, k = int(mask.sum()), e.ds.i[mask].asset_id.nunique()
        if n == 0:
            return {"text": "That selection matches no inspections, so I recorded nothing. Which wells, dates or area do you mean?", "visual": "text", "rows": [], "citations": []}
        field, op = p.get("field") or "wellhead_temp_c", p.get("op") or "set"
        if n > int(os.environ.get("CONFIRM_ROWS", "150")) and not confirmed and self.mode == "ask":
            self.pending[_CUR.get()] = {"plan": p, "who": who, "text": text}
            return self.clarify(f"This would change {n} inspections across {k} wells ({op} {field} = {p['value']}). Apply it that widely?",
                                [f"Apply to all {n}", "No, narrow it down"])
        e.mem.add_correction(author=who, scope_type="selector", scope_id=json.dumps(sel), field=field, op=op,
                             corrected=str(p["value"]), original=f"{n} inspections", reason=p.get("reason") or text, text=text,
                             selector=json.dumps(sel), inspection_id=None)
        e.inspections()                      # refresh the overlay so conflicts are current
        conf = e.overlay_conflicts
        lines = [f"Recorded {who}'s correction ({op} {field} = {p['value']}) for {n} inspections across {k} well(s). Originals are kept; "
                 f"it applies to every user and you can say 'undo that correction' to revoke it. Reason: {p.get('reason') or text}"]
        if conf:
            lines.append(f"Note: it overlaps {len(conf)} earlier correction(s) with different values; the more specific/later one wins "
                         f"(e.g. {conf[0]['inspection']} {conf[0]['field']}: kept {conf[0]['kept']}).")
        return {"text": "\n".join(lines), "visual": "text", "rows": [], "citations": list(e.ds.i[mask].inspection_id[:10])}

    def revoke(self, p, who):
        e = self.e
        fid = p.get("fact_id")
        mine = [f for f in e.mem.facts() if f["author"] == who and f["kind"] in ("correction", "rule", "note", "preference")]
        f = next((x for x in mine if x["id"] == fid), None) if fid else (mine[-1] if mine else None)
        if not f:
            return {"text": "I found nothing of yours to undo.", "visual": "text", "rows": [], "citations": []}
        e.mem.set_status(f["id"], "revoked")
        return {"text": f"Revoked your {f['kind']} #{f['id']} ({(f.get('text') or '')[:80]}). It stays in the audit log but no longer affects answers.",
                "visual": "text", "rows": [], "citations": []}

    def rule(self, p, who):
        e = self.e
        e.mem.add_fact(kind="rule", author=who, scope_type="well_type", scope_id=p["well_type"], field=p.get("rule") or "rca_count",
                       corrected=str(p["value"]), text=p.get("text") or "", reason=p.get("text") or "")
        return {"text": f"Recorded {who}'s rule for all {p['well_type']} wells: {p.get('rule')} = {p['value']} "
                        f"(manual says {e.ds.rules['rca_count'].get(p['well_type'])}). It applies to {p['well_type']} wells only, for every user, "
                        f"and I'll say when an answer follows this rule instead of the manual.",
                "visual": "text", "rows": [], "citations": []}

    def note(self, p, who, text):
        e = self.e
        well, asserts = p.get("well"), p.get("asserts")
        if asserts == "planned_shutdown" and (p.get("valid_from") or "9999") < TODAY_ISO:
            asserts = "not_producing"  # an ongoing shut-in is a claim about the current state
        lines, status = [], "confirmed"
        if p.get("second_hand") and re.search(r"\b(told me|heard|said|says|according to|mentioned)\b", text, re.I):
            status = "unconfirmed"
            lines.append(f"Recorded as second-hand and UNVERIFIED: {who} is relaying what someone else said, and there is no work order or inspection for it yet. "
                         "I did NOT apply it (for example, a recalled pump stays on the recall list) until the person who did the work, or a record, confirms it.")
        elif well and asserts in ("producing", "not_producing"):
            st = e.well_status(well)["rows"][0]
            prod = st["producing"]
            agrees = (asserts == "producing") == prod
            if agrees:
                lines.append(f"Recorded. The latest inspection ({st['inspection']}, {st['inspected_at']}, {st['inspected_by']}) supports this: "
                             f"wellhead {st['delta_c']} °C above air, {well} is {'producing' if prod else 'not producing'}.")
            else:
                status = "unconfirmed"
                lines.append(f"This conflicts with the data: the latest inspection {st['inspection']} on {st['inspected_at']} (by {st['inspected_by']}) shows the wellhead "
                             f"{st['delta_c']} °C above air (limit {st['threshold_c']} °C), so {well} is {'producing' if prod else 'NOT producing'}. "
                             f"I recorded your statement as UNCONFIRMED; can you confirm?")
                for n in st["notes"]:
                    if n["valid_to"] is None or n["valid_to"] >= TODAY_ISO:
                        lines.append(f"Existing note {n['id']} by {n['by']}: {n['text']}")
                for f in e.mem.facts(kind="note"):
                    if f["scope_id"] == well and f["author"] != who and f["field"] == ("producing" if prod else "not_producing"):
                        lines.append(f"{f['author']} stated: \"{f['text']}\" which matches the inspection, not your statement. Both statements stay on record.")
        else:
            span = (f" from {p['valid_from']}" if p.get("valid_from") else "") + (f" to {p['valid_to']}" if p.get("valid_to") else "")
            lines.append(f"Recorded for {well or 'everyone'} as shared knowledge from {who}: \"{(p.get('text') or text)[:200]}\"" + (f" (valid{span})." if span else ".") +
                         " Other users asking about this will see it, attributed to you.")
        if status == "confirmed" and well and re.search(r"swapp|replac", p.get("text") or text, re.I) and "pump" in (p.get("text") or text).lower():
            lines.append(f"From now on {well}'s recalled pump counts as replaced in the recall list. Source: {who}'s own statement, no work order in the system yet; I will say so wherever I use it.")
        e.mem.add_fact(kind="note", author=who, scope_type="well" if well else "fleet", scope_id=well or "*", field=asserts, text=p.get("text") or text,
                       valid_from=p.get("valid_from"), valid_to=p.get("valid_to"), status=status)
        return {"text": "\n".join(lines), "visual": "text", "rows": [], "citations": []}

    def preference(self, p, user_id, who, text):
        e = self.e
        e.mem.add_fact(kind="preference", author=who, scope_type="user", scope_id=user_id, field=json.dumps({"sort": p.get("sort"), "cost_unit": p.get("cost_unit")}), text=p.get("text") or text)
        bits = (["sort wells by area, then well ID"] if p.get("sort") else []) + (["show costs in thousands of dollars"] if p.get("cost_unit") else [])
        return {"text": f"Saved for {who} only (a personal preference, not shared with other users): " + " and ".join(bits) + ". It applies to every list I show you from now on, and I will say so each time.",
                "visual": "text", "rows": [], "citations": []}

    def apply_prefs(self, res, user_id, who):
        """A user's private display preferences, applied to table rows; the answer says so."""
        prefs = [json.loads(f["field"]) for f in self.e.mem.facts(kind="preference") if f["scope_id"] == user_id]
        rows = res.get("rows") or []
        if not prefs or not rows or not isinstance(rows[0], dict):
            return res
        pf = {k: v for d in prefs for k, v in d.items() if v}
        applied = []
        if pf.get("sort") and "Well" in rows[0]:
            rows.sort(key=lambda r: ((r.get("Area") or ""), r["Well"]))
            applied.append("sorted by area, then well ID")
        if pf.get("cost_unit") == "thousands":
            for r in rows:
                for k in [k for k in r if "USD" in k or "cost" in k.lower()]:
                    if isinstance(r[k], (int, float)) and not isinstance(r[k], bool):
                        nk = k.replace("(USD)", "(USD thousands)") if "(USD)" in k else k + " (thousands of USD)"
                        r[nk] = round(r.pop(k) / 1000, 1)
            applied.append("costs in thousands of dollars")
        if applied:
            res["notes"] = list(res.get("notes", [])) + [f"Applied {who}'s own saved display preference (private to them): {', '.join(applied)}."]
        return res
