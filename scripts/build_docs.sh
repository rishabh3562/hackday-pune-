#!/usr/bin/env bash
# Build the PDFs: ./scripts/build_docs.sh   (needs `cd docs-tools && npm install` once and an installed Chromium)
set -euo pipefail
cd "$(dirname "$0")/.."
node docs-tools/build-pdf.mjs WRITEUP.md WRITEUP.pdf --compact          # the 2-page submission write-up
node docs-tools/build-pdf.mjs docs/DIAGRAMS.md docs/DIAGRAMS.pdf --png  # full visual guide + one PNG per diagram
node docs-tools/build-pdf.mjs docs/ARCHITECTURE.md docs/ARCHITECTURE.pdf
.venv/bin/python tests/qa/report.py && node docs-tools/build-pdf.mjs docs/QA_REPORT.md docs/QA_REPORT.pdf   # real answers vs expected, judge scores
# the architecture poster needs the backend running (it renders static/poster.html):  node docs-tools/export-poster.mjs
