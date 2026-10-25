# Docs tooling
Markdown with ```mermaid blocks -> styled PDF (and per-diagram PNGs). Uses the Chromium that `playwright-cli install-browser chromium` already installed.
```
cd docs-tools && npm install          # once: marked, mermaid, playwright-core
node build-pdf.mjs ../WRITEUP.md ../WRITEUP.pdf          # prints page count and diagram count
node build-pdf.mjs ../docs/DIAGRAMS.md ../docs/DIAGRAMS.pdf --png   # --png: one image per diagram, --html: keep the HTML
```
Mermaid also renders natively on GitHub, so the .md files are readable without building anything.
