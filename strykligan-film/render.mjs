// Renderar film.html bild för bild och kodar MP4 med ffmpeg.
// Användning: node render.mjs [stills t1,t2,...]
import { createRequire } from 'module';
import { spawn } from 'child_process';
import fs from 'fs';
const require = createRequire(import.meta.url);
const { chromium } = require('/opt/node22/lib/node_modules/playwright');

const FPS = 30, DUR = 45, URL = 'http://127.0.0.1:8765/film.html?render';
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 540, height: 960 } });
await page.goto(URL);
await page.evaluate(() => window.ready);

const grab = async t => {
  const d = await page.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/jpeg', 0.95); }, t);
  return Buffer.from(d.split(',')[1], 'base64');
};

if (process.argv[2] === 'stills') {
  fs.mkdirSync('stills', { recursive: true });
  for (const t of process.argv[3].split(',').map(Number)) fs.writeFileSync(`stills/t${t.toFixed(2)}.jpg`, await grab(t));
} else {
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-i', 'music.wav', '-c:v', 'libx264', '-preset', 'slow', '-crf', '21', '-maxrate', '3M', '-bufsize', '6M',
    '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level', '4.1', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart',
    'strykligan-fest-2026.mp4'], { stdio: ['pipe', 'inherit', 'inherit'] });
  const n = FPS * DUR;
  for (let i = 0; i < n; i++) {
    const buf = await grab(i / FPS);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 150 === 0) console.log(`bild ${i}/${n}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
}
await browser.close();
