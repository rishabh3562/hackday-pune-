import { chromium } from "playwright-core";
import { readdirSync, existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
function cp(){const root=join(homedir(),"Library/Caches/ms-playwright");for(const d of readdirSync(root).filter(x=>/^chromium-\d+$/.test(x)).sort().reverse())for(const rel of ["chrome-mac-arm64","chrome-mac-x64","chrome-mac"]){const p=join(root,d,rel,"Chromium.app/Contents/MacOS/Chromium");if(existsSync(p))return p;}}
const ex = cp();
const b = await chromium.launch({ executablePath: ex });
const p = await b.newPage({ viewport: { width: 1400, height: 900 } });
const errs = []; p.on("pageerror", (e) => errs.push(String(e))); p.on("console", (m) => m.type() === "error" && errs.push(m.text()));
await p.goto("http://localhost:8000/#/copilot", { waitUntil: "networkidle" });
const info = async (l) => console.log(l, JSON.stringify(await p.evaluate(() => ({ chats: [...document.querySelectorAll("[class*=chat]")].filter(e => e.children.length === 0 || e.tagName === "BUTTON").map(e => e.textContent.trim().slice(0, 40)).filter(Boolean).slice(0, 12), nav: document.querySelector("nav,aside")?.innerText.slice(0, 300) }))));
await info("initial");
const input = await p.$("textarea, input[type=text]");
console.log("input found", !!input);
await input.fill("how many spills in 2026 in Northeast Block 7?"); await p.keyboard.press("Enter");

await new Promise(r => setTimeout(r, 8000));
await p.screenshot({ path: "/tmp/e2e1.png" });
await info("after ask 1");
// new chat
const nb = await p.$$eval("button,a", els => els.map(e => e.textContent.trim()).filter(t => /new chat/i.test(t)));
console.log("new chat buttons", nb);
await p.evaluate(() => [...document.querySelectorAll("button,a")].find(e => /new chat/i.test(e.textContent))?.click());
await new Promise(r => setTimeout(r, 1000));
const input2 = await p.$("textarea, input[type=text]");
await input2.fill("Which wells are not producing in Southwest Block 24?"); await p.keyboard.press("Enter");
await new Promise(r => setTimeout(r, 25000));
await p.screenshot({ path: "/tmp/e2e2.png" });
await info("after ask 2");
await p.reload({ waitUntil: "networkidle" }); await new Promise(r => setTimeout(r, 3000));
await info("after reload");
const list = await p.evaluate(() => fetch("/api/chats?user_id=" + (localStorage.getItem("user") || "U-201")).then(r => r.text()).catch(e => String(e)));
console.log("api", list.slice(0, 300));
console.log("errors", errs.slice(0, 5));
await b.close();
