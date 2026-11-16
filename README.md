# JobHunterX — website

Served by GitHub Pages from this branch (`gh-pages`, root).

- `index.html` — the page
- `assets/style.css`, `assets/app.js` — styles and the built script
- `assets/fonts`, `assets/shots` — bundled fonts and real app screenshots
- `src/` — source: `gl.js` (Three.js stage), `main.js` (GSAP, Lenis, UI)

Rebuild after editing `src/`:

```bash
npm install
```

```bash
npm run build
```

Built with Three.js, GSAP (ScrollTrigger, SplitText) and Lenis — all bundled into `assets/app.js`, nothing loads from a CDN.
