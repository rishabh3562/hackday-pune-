"""Voice front door: a LiveKit agent that talks through Gemini Live (Vertex AI) and answers by calling the SAME copilot backend (/api/ask).
The spoken answer is the copilot's written text; the full visual result (blocks) is sent to the browser over the data channel.
Run:  .venv/bin/python voice/agent.py dev      (needs OMNI_LIVEKIT_URL / _API_KEY / _API_SECRET in .env, gcloud ADC, and the backend on :8000)"""
import asyncio
import json
import os

for line in open(os.path.join(os.path.dirname(__file__), "..", ".env")):          # plain KEY=VALUE .env, no extra dependency
    if "=" in line and not line.startswith("#"):
        k, v = line.strip().split("=", 1); os.environ.setdefault(k, v)
os.environ.setdefault("LIVEKIT_URL", os.environ.get("OMNI_LIVEKIT_URL", ""))
os.environ.setdefault("LIVEKIT_API_KEY", os.environ.get("OMNI_LIVEKIT_API_KEY", ""))
os.environ.setdefault("LIVEKIT_API_SECRET", os.environ.get("OMNI_LIVEKIT_API_SECRET", ""))

import httpx
from livekit.agents import Agent, AgentSession, JobContext, RunContext, WorkerOptions, cli, function_tool
from livekit.plugins import google

BACKEND = os.environ.get("COPILOT_BACKEND_URL", "http://localhost:8000")
MODEL = os.environ.get("VOICE_MODEL", "gemini-live-2.5-flash-native-audio")
INSTRUCTIONS = """You are the voice of an oil-field Asset Intelligence Copilot for well operators. Be brief and natural.
RULE 1: for ANY question or statement about wells, inspections, repairs, spills, compliance, rules, corrections, notes, counts, dates or the fleet, you MUST call the ask_copilot tool
with the user's words (fix obvious speech-to-text slips, e.g. "spills failed in 2026" means spills in 2026, but never invent facts). Never answer such things from memory and never say you cannot get the data without calling the tool first.
RULE 2: say the tool's answer in 2-3 short sentences, reading well and record IDs clearly, and say the full table and details are on screen.
RULE 3: if the tool result starts with "CLARIFYING QUESTION", read that question (and its options) aloud, wait for the user's spoken answer, then call ask_copilot again with their answer in their own words. Keep doing so until you get an answer.
RULE 4: if the tool returns an error, say so briefly and call it once more before giving up. Only for greetings and small talk may you answer without the tool."""


def _brief(r: dict) -> str:
    """Text for the model: the copilot's answer plus a short summary of the table rows (so it never has to say it has no data)."""
    out = (r.get("text") or "").strip()[:700]
    rows = r.get("rows") or []
    if rows and isinstance(rows, list) and isinstance(rows[0], dict):
        cols = [c for c in rows[0] if c not in ("lat", "lon")][:5]
        out += f"\n[{r.get('count', len(rows))} rows on screen; first: " + " | ".join(", ".join(f"{c}={row.get(c)}" for c in cols) for row in rows[:3]) + "]"
    return out


class CopilotVoice(Agent):
    def __init__(self, room, user_id, chat_id):
        super().__init__(instructions=INSTRUCTIONS)
        self.room, self.user_id, self.chat_id = room, user_id, chat_id

    @function_tool
    async def ask_copilot(self, context: RunContext, request: str) -> str:
        """Send the operator's question or statement to the copilot (same tools as the chat) and get its answer back. Use for every fleet or data question.
        Args:
            request: the user's request in their own words, including any well IDs, dates or numbers they said. For a reply to a clarifying question, the user's answer.
        """
        r, err = None, ""
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=90) as http:
                    resp = await http.post(f"{BACKEND}/api/ask", json={"user_id": self.user_id, "chat_id": self.chat_id, "text": request, "mode": "ask"})
                    resp.raise_for_status()
                    r = resp.json()
                break
            except Exception as e:  # noqa: BLE001
                err = f"{type(e).__name__}: {e}"; print("ask_copilot attempt", attempt + 1, "failed:", err, flush=True)
                await asyncio.sleep(1.5)
        if r is None:
            return f"ERROR: the copilot backend did not answer ({err}). Tell the user briefly and offer to retry."
        try:    # the full result is far bigger than a data packet (15 KB), so it goes over a text stream; the browser also accepts the old data topic
            payload = {k: r.get(k) for k in ("text", "visual", "blocks", "options", "citations", "notes", "plan", "context") if r.get(k) is not None}
            await self.room.local_participant.send_text(json.dumps({"question": request, **payload}, default=str), topic="copilot-result")
        except Exception as e:  # noqa: BLE001
            print("ask_copilot: could not send the visual result:", repr(e), flush=True)
        if r.get("visual") == "clarify":
            opts = "; ".join(f"{i}. {o}" for i, o in enumerate(r.get("options", []), 1))
            return f"CLARIFYING QUESTION for the user: {r.get('text') or ''} Options: {opts}"
        return _brief(r) or "The copilot returned no text for that request."


async def entrypoint(ctx: JobContext):
    await ctx.connect()
    p = await ctx.wait_for_participant()
    meta = json.loads(p.metadata or "{}")
    user_id, chat_id = meta.get("user_id", "U-201"), f"voice-{ctx.room.name}"
    session = AgentSession(llm=google.realtime.RealtimeModel(
        model=MODEL, voice="Puck", vertexai=True, project=os.environ.get("GCP_PROJECT", "omni-505707"), location="us-central1", instructions=INSTRUCTIONS, temperature=0.4))
    await session.start(room=ctx.room, agent=CopilotVoice(ctx.room, user_id, chat_id))
    await session.generate_reply(instructions="Greet the operator in one short sentence and ask what they want to look at.")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
