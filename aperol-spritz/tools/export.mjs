// Renders index.html frame by frame and encodes aperol-spritz.mp4 (1920x1080, 30 fps, 30 s).
// Usage: node tools/export.mjs [--stills 1,7,14,20,24,28]
import { chromium } from 'playwright';
import { readFileSync, mkdirSync, rmSync, existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const dir = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const FPS = 30, DURATION = 30;
const args = process.argv.slice(2);
const stills = args[0] === '--stills' ? args[1].split(',').map(Number) : null;
const ffmpeg = process.env.FFMPEG || 'ffmpeg';

// Google Fonts is fetched ahead of time (see README) because the export browser may not reach it.
const fontCss = path.join(dir, '.cache/fonts/inline.css');
const fonts = existsSync(fontCss) ? readFileSync(fontCss, 'utf8') : '';

const page_html = `<!doctype html><html><head><meta charset="utf-8">
<script>window.__capture = true;</script>
<style>${fonts}</style>
<style>body{margin:0!important;padding:0!important}.stage{max-width:none!important}.controls{display:none!important}
#film{border:0!important;border-radius:0!important;width:1920px!important}</style></head><body>
${readFileSync(path.join(dir, 'index.html'), 'utf8')}</body></html>`;

const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await page.setContent(page_html, { waitUntil: 'load', timeout: 60000 });
await page.evaluate(() => document.fonts.ready);
const svg = await page.$('#film');

const outDir = path.join(dir, stills ? 'stills' : '.frames');
rmSync(outDir, { recursive: true, force: true });
mkdirSync(outDir, { recursive: true });

const times = stills ?? Array.from({ length: FPS * DURATION }, (_, i) => i / FPS);
for (let i = 0; i < times.length; i++) {
  await page.evaluate(t => window.renderAt(t), times[i]);
  const name = stills ? `t${String(times[i]).padStart(4, '0')}.png` : `f${String(i).padStart(4, '0')}.png`;
  await svg.screenshot({ path: path.join(outDir, name) });
}
await browser.close();

if (!stills) {
  const r = spawnSync(ffmpeg, ['-y', '-framerate', String(FPS), '-i', path.join(outDir, 'f%04d.png'),
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-movflags', '+faststart',
    path.join(dir, 'aperol-spritz.mp4')], { stdio: 'inherit' });
  rmSync(outDir, { recursive: true, force: true });
  process.exit(r.status ?? 1);
}
