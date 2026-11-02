"""
Application forms that are not plain pages: forms inside an iframe from another site (an embedded Greenhouse / Lever /
Ashby / Workday board on the company's own careers page) and fields inside shadow DOM (web-component upload widgets).

The browser agent's own clicks and typing already reach these (browser-use reads cross-origin iframes). What did not:
  * our one-shot pre-fill and phone scripts ran only in the top page and its same-site frames, so on an embedded form
    they found nothing ("prefill_basic_fields failed");
  * file uploads went through browser-use's upload action, which needs the element it is given to BE an
    <input type=file>; a resume widget whose real input sits in a shadow root (or behind an "Attach" button) failed.

Here every script runs in the page AND in each cross-origin iframe (each is its own CDP target / session), walking open
shadow roots and same-site iframes inside each. Uploads find the real file input wherever it is and set the file on it
by object reference; when a widget has no reachable input at all, the native file chooser that its "Attach" button opens
is intercepted and answered with the file.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable, Callable, Optional

from jobhunterx.config.logging import get_logger

log = get_logger("form_frames")

# Collects every root a form can live in: the document, open shadow roots, and same-site iframes (recursively).
ROOTS_JS = """
  const docs = []; const seenRoots = new Set();
  const addRoot = (r) => {
    if (!r || seenRoots.has(r)) return; seenRoots.add(r); docs.push(r);
    for (const e of r.querySelectorAll('*')) {
      if (e.shadowRoot) addRoot(e.shadowRoot);
      if (e.tagName === 'IFRAME') { try { if (e.contentDocument) addRoot(e.contentDocument); } catch (x) {} }
    }
  };
  addRoot(document);
"""


async def page_sessions(browser_session: Any) -> list[str]:
    """CDP session ids to run a script in: the focused page first, then every cross-origin iframe target."""
    out: list[str] = []
    main = await browser_session.get_or_create_cdp_session()
    out.append(main.session_id)
    try:
        targets = await browser_session._cdp_get_all_pages(include_http=True, include_about=False, include_pages=False,
                                                           include_iframes=True)
        for t in targets:
            if t.get("type") != "iframe":
                continue
            try:
                s = await browser_session.get_or_create_cdp_session(t["targetId"], focus=False)
                if s.session_id not in out:
                    out.append(s.session_id)
            except Exception:
                continue
    except Exception as exc:
        log.debug("iframe_targets_unavailable", error=str(exc)[:120])
    return out


async def eval_everywhere(browser_session: Any, expression: str) -> list:
    """Run a script that returns a list in the page and in every cross-origin iframe; the lists joined."""
    results: list = []
    for sid in await page_sessions(browser_session):
        try:
            out = await browser_session.cdp_client.send.Runtime.evaluate(
                params={"expression": expression, "returnByValue": True, "awaitPromise": True}, session_id=sid)
            value = (out.get("result") or {}).get("value")
            if isinstance(value, list):
                results += value
        except Exception as exc:
            log.debug("eval_in_frame_failed", error=str(exc)[:120])
    return results


# ------------------------------------------------------------------------------------------------- file uploads

# Lists the file inputs in every root, with the words around each one (its label, the section it sits in), and keeps
# them in window.__jhxFiles so the chosen one can be handed back as an object.
_FIND_FILES_JS = "(() => {" + ROOTS_JS + """
  const norm = (s) => (s || '').replace(/\\s+/g, ' ').trim().toLowerCase();
  const up = (e) => e.parentElement || (e.getRootNode && e.getRootNode().host) || null;
  const around = (el) => {
    const bits = [el.name, el.id, el.accept, el.getAttribute('aria-label'), el.title];
    for (const l of el.labels || []) bits.push(l.innerText);
    let c = up(el);
    for (let i = 0; c && i < 7; i++, c = up(c)) {
      const t = norm(c.innerText || c.textContent || '');
      if (t) { bits.push(t.slice(0, 220)); if (t.length > 25) break; }
    }
    return norm(bits.filter(Boolean).join(' | '));
  };
  window.__jhxFiles = [];
  const out = [];
  for (const d of docs) for (const el of d.querySelectorAll('input[type=file]')) {
    window.__jhxFiles.push(el);
    out.push({ i: window.__jhxFiles.length - 1, text: around(el), files: el.files ? el.files.length : 0, disabled: !!el.disabled });
  }
  return out;
})()"""

_WANT = {"resume": ("resume", "cv", "curriculum"), "cover_letter": ("cover",), "cv": ("cv", "curriculum", "resume")}


def _score(kind: str, text: str) -> int:
    s = sum(3 for w in _WANT.get(kind, ()) if w in text)
    if kind != "cover_letter" and "cover" in text:
        s -= 4
    if kind == "cover_letter" and any(w in text for w in ("resume", "curriculum")) and "cover" not in text:
        s -= 4
    if any(w in text for w in ("photo", "image", "avatar", "picture")):
        s -= 5
    return s


async def upload_document(browser_session: Any, kind: str, path: str) -> tuple[bool, str]:
    """Put the file in the right file input — in any frame, inside any shadow root. Returns (done, what happened)."""
    found: list[tuple[str, dict]] = []
    for sid in await page_sessions(browser_session):
        try:
            out = await browser_session.cdp_client.send.Runtime.evaluate(
                params={"expression": _FIND_FILES_JS, "returnByValue": True}, session_id=sid)
            for item in (out.get("result") or {}).get("value") or []:
                found.append((sid, item))
        except Exception:
            continue
    usable = [(sid, it) for sid, it in found if not it.get("disabled")]
    if not usable:
        return False, "no file input on the page"
    ranked = sorted(usable, key=lambda x: -_score(kind, x[1].get("text", "")))
    best_sid, best = ranked[0]
    score = _score(kind, best.get("text", ""))
    # A cover letter or CV goes only into a field that is for it — never into the resume field (it would replace the
    # resume). The resume may go into the one plain, unlabelled file field of a form, but not into one for something else.
    if (kind != "resume" and score <= 0) or (kind == "resume" and (score < 0 or (score == 0 and len(usable) > 1))):
        return False, f"no {kind.replace('_', ' ')} upload field found (the page's file fields: " + \
            "; ".join(it.get("text", "")[:60] or "unlabelled" for _, it in usable[:4]) + ")"
    try:
        ref = await browser_session.cdp_client.send.Runtime.evaluate(
            params={"expression": f"window.__jhxFiles[{int(best['i'])}]", "returnByValue": False}, session_id=best_sid)
        object_id = (ref.get("result") or {}).get("objectId")
        await browser_session.cdp_client.send.DOM.setFileInputFiles(params={"files": [path], "objectId": object_id},
                                                                    session_id=best_sid)
        check = await browser_session.cdp_client.send.Runtime.callFunctionOn(
            params={"objectId": object_id, "returnByValue": True,
                    "functionDeclaration": "function(){ this.dispatchEvent(new Event('input',{bubbles:true}));"
                                           "this.dispatchEvent(new Event('change',{bubbles:true}));"
                                           "return this.files ? this.files.length : 0; }"},
            session_id=best_sid)
        n = (check.get("result") or {}).get("value") or 0
    except Exception as exc:
        return False, f"could not set the file ({str(exc)[:100]})"
    if not n:
        return False, "the page did not take the file"
    return True, f"attached to the field “{best.get('text', '')[:70]}”"


async def upload_via_chooser(browser_session: Any, click: Callable[[], Awaitable[Any]], path: str,
                             timeout: float = 8.0) -> tuple[bool, str]:
    """For a widget with no reachable file input: catch the native file chooser its button opens and answer it with
    the file. `click` presses the button (the agent picked it)."""
    sessions = await page_sessions(browser_session)
    loop = asyncio.get_running_loop()
    opened: asyncio.Future = loop.create_future()

    def on_open(event: dict, session_id: Optional[str] = None) -> None:
        if not opened.done():
            opened.set_result((event, session_id))

    client = browser_session.cdp_client
    try:
        client.register.Page.fileChooserOpened(on_open)
    except Exception as exc:
        return False, f"file chooser not available ({str(exc)[:80]})"
    for sid in sessions:
        try:
            await client.send.Page.enable(session_id=sid)
            await client.send.Page.setInterceptFileChooserDialog(params={"enabled": True}, session_id=sid)
        except Exception:
            continue
    try:
        await click()
        event, sid = await asyncio.wait_for(opened, timeout)
        backend = event.get("backendNodeId")
        if not backend:
            return False, "the file chooser did not say which field it is for"
        await client.send.DOM.setFileInputFiles(params={"files": [path], "backendNodeId": backend}, session_id=sid)
        return True, "attached through the file chooser"
    except asyncio.TimeoutError:
        return False, "no file chooser opened after the click"
    except Exception as exc:
        return False, f"could not answer the file chooser ({str(exc)[:100]})"
    finally:
        for sid in sessions:
            try:
                await client.send.Page.setInterceptFileChooserDialog(params={"enabled": False}, session_id=sid)
            except Exception:
                pass


# ------------------------------------------------------------------------------------------------- required fields

# Every visible field marked required (required / aria-required, or a label ending in "*") that is still empty.
_EMPTY_REQUIRED_JS = "(() => {" + ROOTS_JS + """
  const norm = (s) => (s || '').replace(/\\s+/g, ' ').trim();
  const vis = (e) => { const r = e.getBoundingClientRect(); return r.width > 2 && r.height > 2; };
  const labelOf = (el, d) => {
    let s = [...(el.labels || [])].map((l) => l.innerText).join(' ');
    const lb = el.getAttribute('aria-labelledby');
    if (!s && lb && d.getElementById) s = lb.split(/\\s+/).map((i) => (d.getElementById(i) || {}).innerText || '').join(' ');
    if (!s) s = el.getAttribute('aria-label') || el.placeholder || el.name || '';
    return norm(s);
  };
  const out = [], seenGroups = new Set();
  for (const d of docs) for (const el of d.querySelectorAll('input, select, textarea')) {
    if (['hidden', 'submit', 'button', 'image', 'reset'].includes(el.type) || el.disabled) continue;
    const lab = labelOf(el, d);
    const req = el.required || el.getAttribute('aria-required') === 'true' || /\\*\\s*$/.test(lab);
    if (!req) continue;
    if (el.type === 'file') { if (!(el.files && el.files.length)) out.push((lab || 'file upload') + ' (file)'); continue; }
    if (el.type === 'radio' || el.type === 'checkbox') {
      if (el.type === 'radio' && el.name) {
        if (seenGroups.has(el.name)) continue; seenGroups.add(el.name);
        const group = d.querySelectorAll('input[type=radio][name="' + el.name.replace(/"/g, '') + '"]');
        if ([...group].some((g) => g.checked)) continue;
      } else if (el.checked) continue;
      out.push(lab || el.name || el.type); continue;
    }
    if (!vis(el)) continue;
    if (!norm(el.value)) out.push(lab || el.name || el.id || el.tagName.toLowerCase());
  }
  return out;
})()"""


async def empty_required(browser_session: Any) -> list[str]:
    seen, out = set(), []
    for label in await eval_everywhere(browser_session, _EMPTY_REQUIRED_JS):
        key = str(label).lower()
        if key not in seen:
            seen.add(key)
            out.append(str(label)[:80])
    return out


def as_js_call(fn_source: str, payload: dict) -> str:
    return f"({fn_source})({json.dumps(payload)})"
