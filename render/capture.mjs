// Renders every shot of the canvas grid to ../out/render/r{row}_c{col}.png
import { createServer } from "vite";
import { chromium } from "playwright";
import { mkdirSync, writeFileSync, existsSync, readFileSync } from "node:fs";

const view = JSON.parse(readFileSync(new URL("./view.json", import.meta.url)));
const [W, H] = view.canvas_px;
const cols = W / view.shot_px, rows = H / view.shot_px;
const error = process.argv[2] ?? "2";
const outDir = new URL("../out/render/", import.meta.url).pathname;
mkdirSync(outDir, { recursive: true });

const server = await createServer({ root: new URL(".", import.meta.url).pathname, server: { port: 5175 } });
await server.listen();
const browser = await chromium.launch({ args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: view.shot_px, height: view.shot_px } });
page.on("pageerror", (e) => console.error("page error:", e.message));

if (process.argv[3] === "overview") {
  await page.setViewportSize({ width: 1024, height: 1024 });
  await page.goto(`http://localhost:5175/?overview&shot=1024&error=${error}`);
  await page.waitForFunction(() => window.TILES_LOADED === true, null, { timeout: 300_000, polling: 500 });
  const url = await page.evaluate(() => window.capture());
  writeFileSync(`${outDir}../overview.png`, Buffer.from(url.split(",")[1], "base64"));
  await browser.close();
  await server.close();
  process.exit(0);
}

for (let row = 0; row < rows; row++) {
  for (let col = 0; col < cols; col++) {
    const file = `${outDir}r${row}_c${col}.png`;
    if (existsSync(file)) continue; // resumable
    const t0 = Date.now();
    await page.goto(`http://localhost:5175/?row=${row}&col=${col}&error=${error}`);
    await page.waitForFunction(() => window.TILES_LOADED === true, null, { timeout: 300_000, polling: 500 });
    const url = await page.evaluate(() => window.capture());
    writeFileSync(file, Buffer.from(url.split(",")[1], "base64"));
    console.log(`r${row} c${col} ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
}
await browser.close();
await server.close();
