// Drives a three.js scene in headless Chromium (WebGL via SwiftShader) and streams frames to stdout.
// Each frame: a 512-byte JSON header (screen-space info for the compositor), then W*H*4 bytes of RGBA
// (bottom-up rows, premultiplied alpha).
//
// Usage: node render3d.js <scene.html> <first> <end>        render a frame range
//        node render3d.js <scene.html> <f1,f2,...>           render specific frames
//        env SIZE=2000x2000 sets the canvas size (default 3840x2160); the page reads ?w=&h= from its URL.
const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = __dirname;
const SCENE = process.argv[2];
const FRAMES = process.argv[3].includes(',') ? process.argv[3].split(',').map(Number)
  : Array.from({ length: Number(process.argv[4]) - Number(process.argv[3]) }, (_, i) => Number(process.argv[3]) + i);
const [W, H] = (process.env.SIZE || '3840x2160').split('x').map(Number);
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.ttf': 'font/ttf' };
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

// The browser is restarted every CHUNK frames: Playwright keeps a copy of every uploaded frame it sees,
// so one long-lived page would slowly run out of memory. Scenes are pure functions of t, so chunks are seamless.
const CHUNK = 40;
async function openPage(port) {
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  page.on('console', m => process.stderr.write('[page] ' + m.text() + '\n'));
  page.on('pageerror', e => process.stderr.write('[page error] ' + e.message + '\n'));
  await page.goto(`http://127.0.0.1:${port}/${SCENE}${SCENE.includes('?') ? '&' : '?'}w=${W}&h=${H}`);
  await page.waitForFunction(() => window.READY === true, null, { timeout: 300000 });
  return { browser, page };
}

server.listen(0, '127.0.0.1', async () => {
  const port = server.address().port;
  let browser = null, page = null, done = 0;
  for (const f of FRAMES) {
    if (done % CHUNK === 0) {
      if (browser) await browser.close();
      ({ browser, page } = await openPage(port));
    }
    done++;
    const got = new Promise(r => { deliver = r; });
    const t0 = Date.now();
    const info = await page.evaluate(async f => await window.renderFrame(f), f);
    const buf = await got;
    const head = Buffer.alloc(512, 0x20);
    head.write(JSON.stringify({ f, ...info }));
    for (const b of [head, buf]) if (!process.stdout.write(b)) await new Promise(r => process.stdout.once('drain', r));
    process.stderr.write(`[3d] ${SCENE} frame ${f} ${Date.now() - t0} ms\n`);
  }
  await browser.close();
  server.close();
});
