# Aperol Spritz – receptanimation (30 s)

Förklaringsvideo i HTML/SVG. Tom glas till färdig drink: is, 90 ml prosecco, 60 ml Aperol, 30 ml soda, apelsinskiva, en omrörning.

- `index.html` – animationen. Öppna i webbläsare. Play/Pause, Restart, tidslinje, mellanslag.
- `aperol-spritz.mp4` – färdig video, 1920×1080, 30 fps, 30 s.
- `tools/export.mjs` – renderar `index.html` bild för bild och kodar MP4.

## Exportera video igen

```sh
npm install
# Typsnitt: hämta Google Fonts-CSS med woff2-filerna inbäddade till .cache/fonts/inline.css
# (utan filen används reservtypsnitt).
FFMPEG=/sökväg/till/ffmpeg node tools/export.mjs
node tools/export.mjs --stills 4.8,15,29   # enstaka bildrutor till stills/
```

Animationen är en ren funktion av tiden (`window.renderAt(t)`), så varje bildruta blir identisk oavsett maskin.
