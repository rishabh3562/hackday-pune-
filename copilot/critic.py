"""Critic sub-agent: a stronger model reviews the writer's draft against the tool facts BEFORE the user sees it.
It catches what the deterministic guard cannot: a listed row described as excluded, a claim that contradicts the facts, a missing part of the question.
Used after the deterministic guard, on a different (stronger) model than the writer; one rewrite at most."""
import os

CRITIC_MODEL = os.environ.get("CRITIC_MODEL", "gemini-2.5-pro")
SKIP_TOOLS = {"search_docs", "trace", "sql_query", "root_causes", "well_status_card"}     # text-heavy or ad-hoc: the guard + quotes already cover them

PROMPT = ("You are a strict reviewer of an oil-field copilot's draft answer. You get the QUESTION, the FACTS (JSON from deterministic tools: the only truth) and the DRAFT. "
          'Return JSON {"ok":true|false,"problems":["short, specific"]}. Flag ONLY real problems: (1) the draft contradicts the facts, e.g. says a listed row does not qualify, is excluded, or gets a wrong number/ID/date; '
          "(2) a claim that is not supported by the facts; (3) a listed row/well that is missing; (4) a part of the question that is not answered although the facts contain it; "
          "(5) anything under the facts' notes that explains WHY the result is what it is (a user's rule overriding the manual, a correction, an exclusion, an out-of-date status, 'no recorded reason') but is not stated in the draft: such a note is required content, not optional. Do not flag style or brevity. If the draft is fine, ok=true with no problems.")


def review(question, facts_json, draft):
    from . import agent as A
    prev = A.VERTEX_MODEL; A.VERTEX_MODEL = CRITIC_MODEL
    try:
        out = A.parse_json(A.call_llm([{"role": "system", "content": PROMPT}, {"role": "user", "content": f"QUESTION: {question}\nFACTS: {facts_json[:7000]}\nDRAFT: {draft}"}], 700, json_mode=True, label="critic"))
        return bool(out.get("ok", True)), [str(p)[:200] for p in out.get("problems", [])][:5]
    except Exception:  # noqa: BLE001   (a failing reviewer must never block an answer)
        return True, []
    finally:
        A.VERTEX_MODEL = prev
