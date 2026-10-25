// Markdown (with ```mermaid blocks) -> styled PDF using headless Chromium.   node build-pdf.mjs <in.md> [out.pdf] [--html] [--png] [--compact]
import { readFileSync, writeFileSync, readdirSync, existsSync } from "node:fs";
import { homedir } from "node:os";
import { join, dirname, resolve, basename } from "node:path";
import { fileURLToPath } from "node:url";
import { marked } from "marked";
import { chromium } from "playwright-core";

const here = dirname(fileURLToPath(import.meta.url));
const [, , input, outArg, ...flags] = process.argv;
if (!input) { console.error("usage: node build-pdf.mjs <in.md> [out.pdf] [--html] [--png] [--compact]"); process.exit(1); }
const out = resolve(outArg && !outArg.startsWith("--") ? outArg : input.replace(/\.md$/, ".pdf"));

// find an installed Chromium (installed by `playwright-cli install-browser chromium` or `npx playwright install chromium`)
function chromiumPath() {
  const root = join(homedir(), "Library/Caches/ms-playwright"), linux = join(homedir(), ".cache/ms-playwright");
  for (const base of [root, linux]) {
    if (!existsSync(base)) continue;
    const dirs = readdirSync(base).filter((d) => /^chromium-\d+$/.test(d)).sort((a, b) => +b.split("-")[1] - +a.split("-")[1]);
    for (const d of dirs) {
      for (const rel of ["chrome-mac-arm64/Chromium.app/Contents/MacOS/Chromium", "chrome-mac-x64/Chromium.app/Contents/MacOS/Chromium",
                         "chrome-mac/Chromium.app/Contents/MacOS/Chromium", "chrome-linux/chrome", "chrome-linux64/chrome"]) {
        const p = join(base, d, rel); if (existsSync(p)) return p;
      }
    }
  }
  return undefined;
}

const md = readFileSync(input, "utf8");
const renderer = new marked.Renderer();
const baseCode = renderer.code.bind(renderer);
renderer.code = (tok) => tok.lang === "mermaid" ? `<div class="diagram"><pre class="mermaid">${tok.text}</pre></div>` : baseCode(tok);
const body = marked.parse(md, { renderer, gfm: true });
const mermaidJs = readFileSync(join(here, "node_modules/mermaid/dist/mermaid.min.js"), "utf8");

const css = `
:root{--ink:#1d2433;--mute:#5b6577;--amber:#f5a524;--teal:#0f9d8a;--indigo:#4f46e5;--line:#dfe4ee;--soft:#f6f8fc}
*{box-sizing:border-box} body{font:10.5pt/1.5 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:var(--ink);margin:0}
h1{font-size:21pt;margin:0 0 4pt;padding-bottom:6pt;border-bottom:3px solid var(--amber)}
h2{font-size:14pt;margin:16pt 0 6pt;color:var(--indigo);border-left:5px solid var(--teal);padding-left:8pt}
h3{font-size:11.5pt;margin:12pt 0 4pt;color:var(--teal)} p{margin:5pt 0} code{background:var(--soft);padding:1pt 4pt;border-radius:3pt;font-size:9pt}
pre{background:var(--soft);padding:8pt;border-radius:6pt;overflow:auto;font-size:8.5pt} pre code{background:none;padding:0}
table{border-collapse:collapse;width:100%;margin:8pt 0;font-size:9.2pt} th{background:var(--indigo);color:#fff;text-align:left}
th,td{border:1px solid var(--line);padding:4pt 7pt;vertical-align:top} tr:nth-child(even) td{background:var(--soft)}
blockquote{margin:8pt 0;padding:4pt 10pt;border-left:4px solid var(--amber);background:#fff8ea;color:var(--mute)}
.diagram{margin:10pt 0;padding:8pt;border:1px solid var(--line);border-radius:8pt;background:#fff;text-align:center;page-break-inside:avoid}
.diagram svg{max-width:100%;height:auto} a{color:var(--indigo)} ul,ol{margin:4pt 0 4pt 16pt;padding:0}
@page{size:A4;margin:14mm 13mm}`;
const compact = flags.includes("--compact");   // tight layout for page-limited documents
const css2 = compact ? `body{font-size:8.2pt;line-height:1.32} table{font-size:6.6pt;margin:2pt 0;border-collapse:collapse} td,th{padding:0.6pt 3pt!important;line-height:1.2} h1{font-size:16pt} h2{font-size:11.5pt;margin:8pt 0 3pt} p{margin:3pt 0}
.diagram{margin:5pt 0;padding:4pt} .diagram svg{max-height:150pt;width:auto} @page{margin:9mm 10mm}` : "";
const html = `<!doctype html><html><head><meta charset="utf-8"><title>${basename(input)}</title><style>${css}${css2}</style></head><body>${body}
<script>${mermaidJs}</script>
<script>
mermaid.initialize({startOnLoad:false,theme:"base",securityLevel:"loose",fontFamily:"-apple-system,Segoe UI,Helvetica,Arial,sans-serif",
 themeVariables:{primaryColor:"#e8f7f4",primaryBorderColor:"#0f9d8a",primaryTextColor:"#1d2433",lineColor:"#5b6577",secondaryColor:"#fff4dd",tertiaryColor:"#eef0ff",
 noteBkgColor:"#fff8ea",noteBorderColor:"#f5a524",actorBkg:"#eef0ff",actorBorder:"#4f46e5",signalColor:"#5b6577"},flowchart:{curve:"basis",htmlLabels:true}});
mermaid.run({querySelector:".mermaid"}).then(()=>{window.__done=true}).catch(e=>{window.__done=true;window.__err=String(e)});
</script></body></html>`;

if (flags.includes("--html")) writeFileSync(out.replace(/\.pdf$/, ".html"), html);
const browser = await chromium.launch({ executablePath: chromiumPath() });
const page = await browser.newPage();
await page.setContent(html, { waitUntil: "load" });
await page.waitForFunction("window.__done === true", null, { timeout: 60000 });
const err = await page.evaluate("window.__err || ''");
if (err) console.error("mermaid error:", err);
const nSvg = await page.evaluate("document.querySelectorAll('.mermaid svg').length");
if (flags.includes("--png")) {   // one PNG per diagram, handy for slides and for checking the layout
  const els = await page.$$(".diagram");
  for (let i = 0; i < els.length; i++) await els[i].screenshot({ path: out.replace(/\.pdf$/, `-d${i + 1}.png`) });
}
await page.pdf({ path: out, format: "A4", printBackground: true, margin: compact ? { top: "9mm", bottom: "9mm", left: "10mm", right: "10mm" } : { top: "14mm", bottom: "14mm", left: "13mm", right: "13mm" } });
await browser.close();
const pages = (readFileSync(out).toString("latin1").match(/\/Type\s*\/Page[^s]/g) || []).length;
console.log(`wrote ${out}  (${pages} pages, ${nSvg} diagrams rendered)`);
