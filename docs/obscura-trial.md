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

## Follow-up tests (deal-breakers)

| | Obscura | Chromium |
|---|---|---|
| Attached resume really sent (fetch + FormData, the way React forms send) | **no** — the page shows the file attached (name and size right), but the request leaves the resume field out | yes, PDF bytes arrive |
| Plain HTML form marked `multipart/form-data` | **sent as `x-www-form-urlencoded`** — a file can't travel this way at all | multipart, file included |
| Elements browser-use gives the AI on the Lever application page | **3,463** (310,000 characters, ~78,000 tokens) | 77 |

So with Obscura an application would go out **without the resume** while everything looks fine — the worst kind of
failure for auto-apply. And some pages produce an element list too long for any small model.

## Decision model for picking elements (Keyvix `free/jev-1.13`)

Idea: let a decision model (it answers typed questions — yes/no, pick one option, a score — with probabilities in
~300 ms) pick which element is the name box, the email box, the resume upload and the submit button, instead of the
agent's chat model reading a long list.

What was found:
- `free/jev-1.13` only accepts `POST /v1/decisions` (`state` + named `questions`); chat calls return 400. It cannot
  plan or act — at most it can replace the "which element?" choice. The agent still needs a chat model.
- Free tier: 5 requests a minute per account, 64K-token context (the Lever list above does not fit).
- The service answered **"Service temporarily unavailable" (503) on every call for over 30 minutes** (08:53–09:23 UTC),
  so accuracy could not be measured. `scripts/decision_picker_trial.py` is ready: one call per page asks for all five
  fields, grades each pick against the page, and fills + submits the local test form with the picks
  (`KEYVIX_KEY_FILE=... python -m scripts.decision_picker_trial --obscura ./obscura [--form-only]`).
- Caution: Keyvix's site shows placeholder customer logos and fake-urgency banners; send it no real candidate data.

## Verdict

Not usable for auto-apply today: the resume upload does not reach the company. Not a CAPTCHA fix either. The memory
saving is real; it is worth re-testing when Obscura fixes file uploads in form submissions. A decision model can't fix
these problems — they are in the browser, not in choosing elements.

## Trying it without code changes (admin only)

```
./obscura serve --port 9222 --stealth --allow-file-access          # listens on 127.0.0.1 only
BROWSER_CDP_URL=ws://127.0.0.1:9222/devtools/browser               # in .env, then restart JobHunterX
```

Only the admin (or the local app) uses `BROWSER_CDP_URL`; people who signed themselves up always use their own Browser
Use cloud browser. That is deliberate: the server's browser must not be shared with strangers.

Before any real switch, two code changes would be needed: (1) leave out off-screen elements ourselves when the browser is
Obscura, so the AI prompt stays small; (2) fall back to Chromium when a page fails in Obscura.
