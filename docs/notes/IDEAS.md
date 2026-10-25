# Idea triage

Legend: DONE built · NEXT before the 4pm test data · LATER only if the core is frozen · SKIP not worth the time

| Idea | Verdict | How it fits |
|---|---|---|
| Checklist-based, parallel tracks | DONE | Work is split into engine, memory, agent, tests and UI tracks, each with its own tests. |
| JSONL | NEXT | Ingest already reads JSONL. Also write every answer as one JSONL trace line (question, plan, tool args, citations). The results page becomes reproducible. |
| Gen UI, and several UIs in one response | NEXT | Compound questions become a list of tool calls, rendered as several blocks with one summary. |
| Context management, engineering, harness | DONE / NEXT | Router sees no data; writer sees only tool results. The wiki dossier (about 300 tokens per well) is next. See `docs/ARCHITECTURE.md` section 5. |
| Efficient and best UX for gen UI | LATER | Secondary by decision. Chart switching ("show it as a bar chart") is the one UX item to keep. |
| LLM output validation | NEXT | Grounding check: every ID and number in the prose must appear in the tool result, else regenerate, else use a template. |
| Complex queries and UIs | DONE | 22 extra scenarios with independent ground truth in `tests/extra`. |
| Printable report | LATER | One-page print stylesheet for the morning briefing or a spill incident report. |
| 2-page diagrams and system architecture | NEXT | Write-up page 1 needs one clean architecture diagram. |
| Voice integration | LATER | LiveKit + Gemini Live calling the same `/api/ask`. Last step, after freeze. |
| Show my research paper | SKIP | Not part of the judging. |
| Alerts, notifications, thresholds -> LLM incident reports | LATER | Facts from the compliance tool (SR-01 countdown, open fines); the LLM only writes the narrative. |
| Dashboard first | NEXT (small) | Zero-prompt morning briefing: newly stopped wells, stale statuses, overdue reports, open fines. |
| Context limits (date range, particular sensors) | DONE | Every tool takes area, well and period; sensors are limited to wellhead and ambient temperature in this data. |
| Skill.md, gbrain, LLM wiki | NEXT (deterministic part) | Rules registry with source section, plus per-well dossiers. LLM-written insights stay LATER. mem0 and gbrain rejected: no scope or audit trail. |
