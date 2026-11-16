# JobHunterX — website

The public website for [JobHunterX](https://github.com/kvcops/JobHunterX), served by GitHub Pages from the `gh-pages` branch.

```
index.html          the whole page: HTML, CSS, JavaScript and every illustration (inline SVG)
assets/fonts/       Instrument Serif, Geist, Geist Mono (SIL Open Font License), so nothing loads from a CDN
assets/shots/       real screenshots from the main repository, converted to WebP
assets/favicon.svg  the cross-stitch mark
.nojekyll           tells GitHub Pages to serve files as they are
```

Open `index.html` directly, or serve the folder (`python -m http.server`) to preview.
The download buttons use `releases/latest/download/<file>` links, so they always point to the newest desktop release.
Installer sizes and the version number are read live from the GitHub API when available; the page works without them.
