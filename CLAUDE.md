# CLAUDE.md: Asset Intelligence Copilot (team guide)

Shared context for everyone (and every Claude Code session) working in this repo. Keep it short and true; update it when reality changes.

## What this project is
A chat copilot that answers operators' plain-English questions about oil wells (FlytBase Hack Day challenge).
**Design rule:** typed, deterministic tools do all the arithmetic and rule application; the LLM only routes a question to a tool and writes the summary; code checks the prose before it is shown. Do not move logic into prompts.

## Stack (verified from the code)
- Python, FastAPI + uvicorn: `copilot/server.py` (backend and the build-free UI in `static/`)
- Data: pandas, DuckDB (`store.py`), Chroma + BM25 (`search.py`), SQLite memory (`memory.py`)
- LLM layer: `copilot/agent.py` (`_call_llm`, `_vertex`, `_gemma`, OpenRouter fallback); critic in `critic.py`
- Optional: `web/` (Next.js + CopilotKit chat UI, a thin client of the backend `/agui`), `voice/` (LiveKit)

## Run it (Windows, Git Bash, repo root)
```bash
uv venv .venv && uv pip install -p .venv/Scripts/python.exe -r requirements.txt   # once
git clone --depth 1 https://github.com/FlytBaseAILabs/flytbase-ahc-swe-asset-intelligence-dataset data/repo   # once
cp .env.example .env    # then fill in keys; never commit .env

export DATA_DIRS=data/repo/sample-data COPILOT_TODAY=2026-10-17
.venv/Scripts/python.exe -m uvicorn copilot.server:app --port 8000     # backend + plain UI -> http://localhost:8000
cd web && npm install && npm run dev                                   # optional chat UI -> http://localhost:3000 (needs 8000 running)
```
Test set instead of sample: `DATA_DIRS=data/repo/test-data/dataset COPILOT_TODAY=2027-01-15`.
Port 8000 is the real app; 3000 only forwards chat to it. macOS/Linux: use `.venv/bin/python`.

## Tests (run before every PR)
- `.venv/Scripts/python.exe tests/golden.py` needs no LLM. Sample data passes 18/18. Test data has 6 known failures (see `tests/results/golden.json`); do not "fix" them by editing expectations.
- Others: `tests/extra/run.py`, `tests/chat/run.py`, `tests/bench_router.py` (model-based, needs credentials).

## Working agreements
- Branch per person or feature (`name/topic`), PR into `main`. Never push to `main` directly.
- Secrets live only in `.env` (git-ignored). Never paste keys into code, chat, docs or commits.
- Ask the team before installing new dependencies or changing the architecture.
- Keep edits small and match the surrounding style (terse, few comments).
- Tests that write to `tests/results/` change tracked files; don't commit those unless the run is the point of the PR.
- Update `docs/ARCHITECTURE.md` when behavior changes.

## Sponsor tools: current plan
Full plan: `docs/TEAM_PLAN.md`. Summary:
- **Jarvislabs Model APIs** (OpenAI-compatible, base URL `https://models.jarvislabs.net/v1`, key in `JARVISLABS_API_KEY`). Target model: Gemma 4 26B A4B IT. Exact model ID is **unconfirmed**; read it from the Jarvislabs dashboard.
- **Kepler by RubixKube**: desktop SRE assistant with automations (steps, Decide, Post, chat triggers) and hooks. It is an operator layer around the app, not a library. Install, Windows support, and how it reaches `localhost:8000` are **unverified**.
- **Temporal**: optional stretch only. Not started.

## Known gotchas
- `_gemma` ignores `json_mode`, but the planner needs JSON; a new backend must handle it.
- `_call_llm` swallows errors and silently falls back, so failures are invisible today.
- `static/index.html` loads Chart.js and Leaflet from CDNs; charts and maps break offline.
