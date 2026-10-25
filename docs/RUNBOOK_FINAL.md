# Runbook for the final two hours

1. **Freeze** `main` (all suites green: golden, 22 extra, 29 design-review, blocks, sql, router, ui-syntax).
2. Put the released test dataset anywhere (e.g. `data/test/`); it must contain `fleet/` and `assets/` (the loader also finds them one or two levels down).
3. **Load check** (no LLM): `./scripts/final_run.sh data/test questions.txt` prints wells/inspections/repairs/reports/areas and any rule-parsing warnings first.
   - New wells, areas, users and a second root are merged by ID; loading a root twice is idempotent.
   - If a rule warning appears (document wording differs) the sample value is used (e.g. the SR-01 deadline now parses both 24 h and 12 h from the revision text) and the warning is shown in Audit > Data & ingest.
4. Write the final questions into `questions.txt` as `User Name: question` lines (`--- new chat` between chats). Order matters: memory is fresh and state-building lines (corrections, notes) come before the questions that depend on them.
5. **Run:** the script uses `COPILOT_CLARIFY=auto` (nobody answers clarifying questions; it states "Assumed: ...") and writes `RESULTS.md` with every answer, its table rows, notes and evidence IDs.
6. **Spot-check** numbers against the tools: open the UI, switch user, ask the same question, and look at Audit > Traces (plan, tool, arguments) and the Wiki page of the well. Anything odd: `tests/qa/run_answers.py --judge` style grading works on any question list.
7. **Page 2** of `WRITEUP.md`: paste what worked / what did not and why from `RESULTS.md`; `./scripts/build_docs.sh` builds the PDFs and checks the page count.
8. **Submit:** public repo (MIT), write-up PDF, 5-minute video (UI: Overview -> Copilot answer with visuals + clarification -> correction and recall -> Wiki -> Audit -> voice), repository link.
