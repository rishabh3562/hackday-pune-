"""AG-UI endpoint (open Agent-User Interaction protocol) so CopilotKit can drive the copilot.
POST /agui  body: RunAgentInput  ->  SSE stream of events:
  RUN_STARTED, TEXT_MESSAGE_START/CONTENT/END (the written answer), TOOL_CALL_START/ARGS/END (name=show_result, args = typed UI spec),
  RUN_FINISHED.  The frontend renders `show_result` with the same spec the plain UI uses."""
import json
import uuid

from ag_ui.core import (EventType, RunFinishedEvent, RunStartedEvent, TextMessageContentEvent, TextMessageEndEvent,
                        TextMessageStartEvent, ToolCallArgsEvent, ToolCallEndEvent, ToolCallStartEvent)
from ag_ui.encoder import EventEncoder
from fastapi import Request
from fastapi.responses import StreamingResponse


def _last_user_text(messages):
    for m in reversed(messages or []):
        role = m.get("role") if isinstance(m, dict) else getattr(m, "role", None)
        if role == "user":
            c = m.get("content") if isinstance(m, dict) else m.content
            if isinstance(c, list):
                c = " ".join(p.get("text", "") for p in c if isinstance(p, dict))
            return c or ""
    return ""


def mount(app, agent, default_user="U-201"):
    enc = EventEncoder()

    @app.post("/agui")
    async def agui(request: Request):
        body = await request.json()
        thread, run = body.get("threadId") or str(uuid.uuid4()), body.get("runId") or str(uuid.uuid4())
        props = body.get("forwardedProps") or {}
        state = body.get("state") or {}
        user = props.get("user_id") or state.get("user_id") or request.headers.get("x-user-id") or default_user
        text = _last_user_text(body.get("messages"))

        async def stream():
            yield enc.encode(RunStartedEvent(type=EventType.RUN_STARTED, thread_id=thread, run_id=run))
            out = agent.ask(user, thread, text) if text else {"text": "Ask me about your wells.", "visual": "text", "rows": []}
            mid = str(uuid.uuid4())
            yield enc.encode(TextMessageStartEvent(type=EventType.TEXT_MESSAGE_START, message_id=mid, role="assistant"))
            yield enc.encode(TextMessageContentEvent(type=EventType.TEXT_MESSAGE_CONTENT, message_id=mid, delta=out.get("text") or ""))
            yield enc.encode(TextMessageEndEvent(type=EventType.TEXT_MESSAGE_END, message_id=mid))
            spec = {k: out.get(k) for k in ("visual", "rows", "parts", "months", "pending", "notes", "citations", "options", "blocks") if out.get(k) is not None}
            if spec.get("blocks") or spec.get("visual") == "clarify":
                tid = str(uuid.uuid4())
                yield enc.encode(ToolCallStartEvent(type=EventType.TOOL_CALL_START, tool_call_id=tid, tool_call_name="show_result", parent_message_id=mid))
                yield enc.encode(ToolCallArgsEvent(type=EventType.TOOL_CALL_ARGS, tool_call_id=tid, delta=json.dumps(spec, default=str)))
                yield enc.encode(ToolCallEndEvent(type=EventType.TOOL_CALL_END, tool_call_id=tid))
            yield enc.encode(RunFinishedEvent(type=EventType.RUN_FINISHED, thread_id=thread, run_id=run))

        return StreamingResponse(stream(), media_type=enc.get_content_type())
