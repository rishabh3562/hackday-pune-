#!/usr/bin/env bash
# Final-questions routine. Usage: ./scripts/final_run.sh <path-to-test-dataset-folder> <questions.txt> [out.md]
#   test dataset folder = the folder that contains fleet/ and assets/ (or its parent, the loader finds it)
#   questions.txt       = lines "User Name: question", '--- new chat' between chats (see tests/final_questions_sample.txt)
set -euo pipefail
cd "$(dirname "$0")/.."
TEST="${1:?path to the test dataset}"; Q="${2:?questions file}"; OUT="${3:-RESULTS.md}"
echo "== pre-flight =="; .venv/bin/python tests/golden.py | tail -1; .venv/bin/python tests/ui_syntax_test.py | tail -1
echo "== load check (test data only) =="
.venv/bin/python - "$TEST" <<'PY'
import sys; sys.path.insert(0, ".")
from copilot.data import Dataset
d = Dataset(sys.argv[1])
print(len(d.w), "wells,", len(d.i), "inspections,", len(d.m), "repairs,", len(d.reports), "reports,", len(d.areas), "areas;", "warnings:", d.warnings or "none")
PY
echo "== running the questions (fresh memory, clarify mode auto) =="
COPILOT_TODAY="${COPILOT_TODAY:-2027-01-15}" COPILOT_CLARIFY=auto .venv/bin/python -u tests/run_final.py "$Q" "$OUT" "$TEST"
echo "== done: $OUT  (paste into page 2 of WRITEUP.md; then ./scripts/build_docs.sh) =="
