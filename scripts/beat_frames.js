// Renders one frame per beat (plus optional extra times) to out/beats/, for review before the full render.
const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');
(async () => {
  const outDir = path.resolve(process.argv[2] || 'out/beats'); fs.mkdirSync(outDir, { recursive: true });
  const extra = (process.argv[3] || '').split(',').filter(Boolean).map(Number);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto('file://' + path.resolve('index.html'));
  const B = 60 / 90;
  const times = [];
  for (let b = 0; b < 15; b++) times.push([`b${String(b).padStart(2, '0')}`, b * B + 0.12]);
  for (const t of extra) times.push([`t${t.toFixed(3)}`, t]);
  for (const [name, t] of times) {
    await page.evaluate(([t]) => window.seek(t, 1 / 180), [t]);
    await page.locator('canvas').screenshot({ path: `${outDir}/${name}.png` });
  }
  await browser.close();
})();
