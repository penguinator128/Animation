// Full render: 60 fps, 3 subframes per frame (each with in-page motion blur over its slice of the shutter),
// piped to ffmpeg, blended with tmix, then muxed with the soundtrack rendered by OfflineAudioContext.
const { chromium } = require('playwright');
const { spawn, execFileSync } = require('child_process');
const path = require('path'), fs = require('fs');
(async () => {
  fs.mkdirSync('out', { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto('file://' + path.resolve('index.html'));
  const wav = await page.evaluate(() => window.renderSoundtrack());
  fs.writeFileSync('out/soundtrack.wav', Buffer.from(wav, 'base64'));
  console.log('audio written');
  const FPS = 60, SUB = 3, DUR = 10, frames = FPS * DUR;
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS * SUB), '-i', '-',
    '-vf', `tmix=frames=${SUB}:weights='1 1 1',select='eq(mod(n\\,${SUB})\\,${SUB - 1})',setpts=N/${FPS}/TB`,
    '-r', String(FPS), '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p', 'out/video_silent.mp4'], { stdio: ['pipe', 'inherit', 'inherit'] });
  const shutter = 1 / (FPS * SUB);
  for (let f = 0; f < frames; f++) {
    for (let s = 0; s < SUB; s++) {
      const t = (f + (s + 1) / SUB) / FPS; // frame f spans [f/60, (f+1)/60]
      await page.evaluate(([t, sh]) => window.seek(t, sh), [t, shutter]);
      const png = await page.locator('canvas').screenshot({ type: 'png' });
      if (!ff.stdin.write(png)) await new Promise(r => ff.stdin.once('drain', r));
    }
    if (f % 60 === 0) console.log('frame', f);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await browser.close();
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', 'out/video_silent.mp4', '-i', 'out/soundtrack.wav',
    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-shortest', '-movflags', '+faststart', 'ASTRIS-logo-reveal.mp4']);
  console.log('done');
})();
