// Renders static/poster.html (served by the running backend) to docs/img/architecture.png and docs/ARCHITECTURE_POSTER.pdf.   node export-poster.mjs [base-url]
import { chromium } from "playwright-core";
import { readdirSync, existsSync } from "node:fs"; import { homedir } from "node:os"; import { join, dirname, resolve } from "node:path"; import { fileURLToPath } from "node:url";
const root = resolve(dirname(fileURLToPath(import.meta.url)), ".."), base = process.argv[2] || "http://localhost:8000";
const dir = join(homedir(), "Library/Caches/ms-playwright"); let exe;
for (const d of readdirSync(dir).filter((x) => /^chromium-\d+$/.test(x)).sort((a, b) => +b.split("-")[1] - +a.split("-")[1])) for (const r of ["chrome-mac-arm64", "chrome-mac-x64", "chrome-mac"]) { const p = join(dir, d, r, "Chromium.app/Contents/MacOS/Chromium"); if (!exe && existsSync(p)) exe = p; }
const b = await chromium.launch({ executablePath: exe }), p = await b.newPage({ viewport: { width: 1500, height: 1000 }, deviceScaleFactor: 2 });
await p.emulateMedia({ colorScheme: "light" }); await p.goto(`${base}/static/poster.html`); await p.waitForSelector(".poster .pcard");
await p.locator(".poster").screenshot({ path: join(root, "docs/img/architecture.png") });
const h = await p.evaluate(() => document.querySelector(".poster").scrollHeight);
await p.pdf({ path: join(root, "docs/ARCHITECTURE_POSTER.pdf"), width: "1500px", height: `${h + 60}px`, printBackground: true, pageRanges: "1" });
await b.close(); console.log("wrote docs/img/architecture.png and docs/ARCHITECTURE_POSTER.pdf");
