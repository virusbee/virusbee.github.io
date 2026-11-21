#!/usr/bin/env node
/**
 * Batch viewport audit with Playwright.
 *
 * Usage:
 *   python3 -m http.server 8000
 *   node .agents/skills/workbuddy-replica/scripts/audit_viewport.mjs \
 *     --url http://localhost:8000 --out .audit
 *
 * Requires Playwright (`npm i -D playwright` or global install).
 * For an existing browser install: `npx playwright install chromium`.
 */

import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const VIEWPORTS = [
  { name: "desktop-1440", width: 1440, height: 900 },
  { name: "laptop-1024", width: 1024, height: 768 },
  { name: "tablet-768", width: 768, height: 900 },
  { name: "tablet-656", width: 656, height: 900 },
  { name: "mobile-560", width: 560, height: 800 },
  { name: "mobile-375", width: 375, height: 812 },
  { name: "mobile-320", width: 320, height: 700 },
];

function parseArgs(argv) {
  const out = { url: "", out: ".audit", wait: 350, reducedMotion: false, ignore: [] };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--url") out.url = argv[++i] ?? "";
    else if (arg === "--out") out.out = argv[++i] ?? out.out;
    else if (arg === "--wait") out.wait = Number(argv[++i] ?? out.wait);
    else if (arg === "--reduced-motion") out.reducedMotion = true;
    else if (arg === "--ignore") out.ignore = (argv[++i] ?? "").split(",").map(s => s.trim()).filter(Boolean);
    else if (arg === "--help" || arg === "-h") {
      console.log("Usage: node audit_viewport.mjs --url http://localhost:8000 [--out .audit] [--wait 350] [--reduced-motion] [--ignore '.drawer,.toast']");
      process.exit(0);
    }
  }
  if (!out.url) {
    console.error("Missing --url. Start a local server first, then pass its URL.");
    process.exit(2);
  }
  return out;
}

async function loadChromium() {
  try {
    const mod = await import("playwright");
    return mod.chromium;
  } catch {
    console.error("Playwright is not installed. Run: npm i -D playwright && npx playwright install chromium");
    process.exit(2);
  }
}

const args = parseArgs(process.argv.slice(2));
const chromium = await loadChromium();
await mkdir(args.out, { recursive: true });

const browser = await chromium.launch();
const results = [];
let failed = false;

for (const vp of VIEWPORTS) {
  const context = await browser.newContext({
    viewport: { width: vp.width, height: vp.height },
    deviceScaleFactor: 1,
    reducedMotion: args.reducedMotion ? "reduce" : "no-preference",
  });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", msg => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", err => consoleErrors.push(String(err)));

  await page.goto(args.url, { waitUntil: "load", timeout: 30000 });
  await page.waitForTimeout(args.wait);

  const metrics = await page.evaluate(({ ignore }) => {
    const doc = document.documentElement;
    const vw = doc.clientWidth;
    const sw = doc.scrollWidth;
    const ignored = (el) => ignore.some(sel => {
      try { return el.closest(sel); } catch { return false; }
    });
    const offenders = [...document.querySelectorAll("body *")]
      .filter(el => {
        if (ignored(el)) return false;
        const s = getComputedStyle(el);
        if (s.display === "none" || s.visibility === "hidden" || s.opacity === "0") return false;
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.right > vw + 0.5;
      })
      .slice(0, 20)
      .map(el => ({
        tag: el.tagName.toLowerCase(),
        cls: typeof el.className === "string" ? el.className.slice(0, 120) : "",
        right: Math.round(el.getBoundingClientRect().right * 10) / 10,
        width: Math.round(el.getBoundingClientRect().width * 10) / 10,
      }));
    return { vw, sw, overflow: sw > vw, offenders };
  }, { ignore: args.ignore });

  const shot = path.join(args.out, `${vp.name}.png`);
  await page.screenshot({ path: shot, fullPage: true });

  const ok = !metrics.overflow && metrics.offenders.length === 0 && consoleErrors.length === 0;
  if (!ok) failed = true;
  results.push({ ...vp, ...metrics, consoleErrors, screenshot: shot, ok });

  console.log(`${ok ? "PASS" : "FAIL"} ${vp.name} ${vp.width}x${vp.height} scrollW=${metrics.sw} vw=${metrics.vw} offenders=${metrics.offenders.length} console=${consoleErrors.length}`);
  for (const item of metrics.offenders) console.log(`  overflow ${item.tag}.${item.cls} right=${item.right} width=${item.width}`);
  for (const err of consoleErrors) console.log(`  console ${err}`);
  await context.close();
}

await browser.close();
await writeFile(path.join(args.out, "result.json"), JSON.stringify(results, null, 2), "utf8");
console.log(`\nwrote ${path.join(args.out, "result.json")}`);
process.exit(failed ? 1 : 0);
