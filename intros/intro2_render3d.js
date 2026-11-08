// Drives the intro 2 three.js scene in headless Chromium (WebGL via SwiftShader) and streams frames to stdout.
// Each frame: a 512-byte JSON header (screen-space info for the compositor), then 3840*2160*4 bytes of RGBA
// (bottom-up rows, premultiplied alpha). Usage: node intro2_render3d.js <first> <end> | <f1,f2,...>
const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = __dirname;
// frames: "<first> <end>" for a range, or a comma-separated list
const FRAMES = process.argv[2].includes(',') ? process.argv[2].split(',').map(Number)
  : Array.from({ length: Number(process.argv[3]) - Number(process.argv[2]) }, (_, i) => Number(process.argv[2]) + i);
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json' };
let deliver = null;

const server = http.createServer((req, res) => {
  if (req.method === 'POST' && req.url.startsWith('/frame')) {
    const chunks = [];
    req.on('data', c => chunks.push(c));
    req.on('end', () => { res.end('ok'); deliver(Buffer.concat(chunks)); });
    return;
  }
  const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(ROOT) || !fs.existsSync(p)) { res.statusCode = 404; return res.end(); }
  res.setHeader('Content-Type', TYPES[path.extname(p)] || 'application/octet-stream');
  fs.createReadStream(p).pipe(res);
});

server.listen(0, '127.0.0.1', async () => {
  const port = server.address().port;
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 3840, height: 2160 }, deviceScaleFactor: 1 });
  page.on('console', m => process.stderr.write('[page] ' + m.text() + '\n'));
  page.on('pageerror', e => process.stderr.write('[page error] ' + e.message + '\n'));
  await page.goto(`http://127.0.0.1:${port}/intro2_scene.html`);
  await page.waitForFunction(() => window.READY === true, null, { timeout: 300000 });
  for (const f of FRAMES) {
    const got = new Promise(r => { deliver = r; });
    const t0 = Date.now();
    const info = await page.evaluate(async f => await window.renderFrame(f), f);
    const buf = await got;
    const head = Buffer.alloc(512, 0x20);
    head.write(JSON.stringify({ f, ...info }));
    for (const b of [head, buf]) if (!process.stdout.write(b)) await new Promise(r => process.stdout.once('drain', r));
    process.stderr.write(`[3d] frame ${f} ${Date.now() - t0} ms\n`);
  }
  await browser.close();
  server.close();
});
