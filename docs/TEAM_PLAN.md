# Team plan: Gemma on Jarvislabs + Kepler operations layer

Goal for the 3-hour build: the copilot answers through **Gemma 4 on Jarvislabs**, and **Kepler** watches the app and explains failures. Pick a task, put your name on it, tick it off. Use one branch per task (`name/topic`).

## Status of unknowns (resolve first, 15 min)
| # | Question | Owner | Answer |
|---|---|---|---|
| 1 | Exact Jarvislabs model ID for Gemma 4 26B A4B IT (dashboard) | | |
| 2 | Does the model return clean JSON? (planner needs it) | | |
| 3 | Kepler: installed, logged in, runs on Windows? | | |
| 4 | Can Kepler reach `http://localhost:8000`, or do we need a tunnel? | | |
| 5 | Which chat channel for Kepler's Post step (Slack/Telegram/other)? | | |

## Tasks
### T1. Jarvislabs backend (about 45 min) `copilot/agent.py`
- [ ] Add `_jarvis(messages, max_tokens, json_mode)` next to `_gemma` using base URL `https://models.jarvislabs.net/v1`, key from `JARVISLABS_API_KEY`, model from `JARVIS_MODEL`.
- [ ] Select with `COPILOT_BACKEND=jarvis` in `_call_llm`; record real token usage in `_USAGE`.
- [ ] Handle `json_mode` (prompt instruction and/or response format, whichever the model supports); keep the planner's retry path working.
- [ ] Add the three env vars to `.env.example` (no values).
- **Done when:** a question in the UI is answered with `COPILOT_BACKEND=jarvis`, and the Audit page shows the Jarvis model.

### T2. Benchmark (about 20 min) `tests/bench_router.py`
- [ ] Run the router benchmark on the Jarvis backend; save the result next to `router-gemini.json` and `router-gemma.json`.
- **Done when:** a Gemini vs Gemma (Vertex) vs Gemma (Jarvis) table exists in the PR description. Baselines: Gemini 40/40, Gemma 35/40.

### T3. Make failures visible (about 30 min) `copilot/agent.py`, `copilot/audit.py`
- [ ] Log each LLM failure and fallback (backend, error, latency, time) instead of swallowing it in `_call_llm`.
- [ ] Surface it through the existing Health audit endpoint so Kepler has something to read.
- **Done when:** with a wrong key, the Health endpoint shows the error and the fallback taken.

### T4. Kepler automation (about 60 to 75 min, no repo code except docs)
- [ ] Install Kepler, connect it to the running backend.
- [ ] `/triage` automation: fetch Health and recent traces, **Decide** step classifies the failure (LLM unavailable / bad JSON / data problem), **Post** step sends the summary.
- [ ] Second automation: run `tests/golden.py` and report failures.
- [ ] Write what worked and what didn't in `docs/KEPLER.md`.
- **Done when:** breaking the key triggers a correct, readable triage message.

### T5. Demo and docs (about 30 min)
- [ ] Script: normal answer, break the key, copilot degrades, Kepler explains.
- [ ] Update `docs/ARCHITECTURE.md` (models section) and `README.md`.

### Stretch (only if time remains)
- Temporal: retrying workflow around wiki insight generation. Needs the `temporalio` package and a Temporal dev server; agree as a team before installing.

## Rules of the road
- Port 8000 is the real app; 3000 is a thin chat client. Develop against 8000.
- Never commit `.env`, keys, or `data/`. Confirm with `git status` before committing.
- Run `tests/golden.py` (sample data must stay 18/18) before opening a PR.
