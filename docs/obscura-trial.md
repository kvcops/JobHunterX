# Obscura trial (auto-apply browser)

What was tested: [Obscura](https://github.com/h4ckf0r0day/obscura) 0.2.6 (official Linux build, `--stealth`) against
headless Chromium 153, both driven the way JobHunterX drives its browser — over CDP, the `BROWSER_CDP_URL` setting.
Same machine, same tasks, two full runs (numbers below are from run 2; run 1 was the same within ~10%).
Script: `jobhunterx/scripts/browser_trial.py` (run it yourself: `python -m scripts.browser_trial --obscura ./obscura`).

Real application pages were only filled in, never submitted.

## Results

| | Obscura | Chromium |
|---|---|---|
| Start-up | **0.02 s** | 0.25–1.4 s |
| RAM when idle (PSS) | **24 MB** | 298 MB |
| RAM at the busiest point | **162 MB** | 1,094 MB |
| Greenhouse page load | 1.5 s | **0.6 s** |
| Lever page load | 2.2 s | **1.0 s** |
| Ashby page load (React app) | 1.1 s | **0.6 s** |
| Pages look right (screenshots) | yes — very close to Chrome | yes |
| Name field found and filled (Greenhouse, Lever, Ashby) | yes (Greenhouse fill failed once in 2 runs) | yes |
| **Agent (browser-use) types into a field** | yes | yes |
| **Agent uploads the resume** | yes — only with `--allow-file-access` | yes |
| Agent reads the page (time) | 0.1–0.5 s | 0.1–0.3 s |
| **Elements the AI has to choose from** — Greenhouse / Ashby | **289 / 127** | 8 / 40 |
| Live view in the app (screencast frames) | yes, 7 frames in 2.4 s | yes, 7 frames |
| "Take over": your clicks and typing | yes | yes |
| reCAPTCHA scripts load (Greenhouse, Google demo) | yes | yes |
| Bot-check page (bot.sannysoft.com) failed checks | 3 | 4 |
| `navigator.webdriver` | false | false |
| Playwright's own file upload (`set_input_files`) | **no** (`DataTransfer is not defined`) | yes |

## What this means

Good:
- **About 7× less memory.** 24 MB idle and ~160 MB at peak, against ~300 MB idle and ~1.1 GB at peak for Chromium. On a
  small VPS this is the biggest win: several applications could run at once where Chromium fits one.
- Starts instantly.
- Everything JobHunterX's agent actually uses works: reading the page, typing, uploading the resume (through
  browser-use's own upload), the live view and taking over.
- Pages render very close to Chrome, including the React-heavy Ashby form.

Not good:
- **Pages load about 2× slower** than Chromium here.
- **The AI sees far too many elements**: 289 on a Greenhouse page where Chromium gives 8. Obscura reports everything on the
  page as visible, so browser-use cannot leave out what is off-screen. That means much longer AI prompts on every step:
  slower, more costly on paid models, and more room for the AI to click the wrong thing.
- It needs `--allow-file-access` for uploads. Then anything that can reach its port can read local files — it must only
  listen on 127.0.0.1 (the default).
- Small rough edges: a fill that failed once on Greenhouse; Playwright's own upload call does not work (the app does not
  use it, but other tools might); the reCAPTCHA badge draws as an empty box.
- **CAPTCHAs: no clear win.** The bot-check page scores it about the same as plain headless Chrome. Its stealth hides
  the "this is automation" signs, but the biggest CAPTCHA trigger on a VPS is the data-centre IP address, and Obscura
  does not change that (a residential proxy, like Browser Use's, does). Whether Google scores it well on real
  reCAPTCHA could not be measured here.
- It is a young, independent engine ("may differ from Chromium", says its own README). Job portals change often; every
  difference becomes a failed application that is hard to debug.

## Verdict

Not a replacement for Browser Use's cloud browser yet, and not a CAPTCHA fix. It **is** a good lighter option for
running the browser on the server itself, if memory is the problem — worth a small, opt-in experiment, not a switch.

## Trying it without code changes (admin only)

```
./obscura serve --port 9222 --stealth --allow-file-access          # listens on 127.0.0.1 only
BROWSER_CDP_URL=ws://127.0.0.1:9222/devtools/browser               # in .env, then restart JobHunterX
```

Only the admin (or the local app) uses `BROWSER_CDP_URL`; people who signed themselves up always use their own Browser
Use cloud browser. That is deliberate: the server's browser must not be shared with strangers.

Before any real switch, two code changes would be needed: (1) leave out off-screen elements ourselves when the browser is
Obscura, so the AI prompt stays small; (2) fall back to Chromium when a page fails in Obscura.
