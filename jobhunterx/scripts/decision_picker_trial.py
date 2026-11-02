"""Trial: can a "decision model" (Keyvix / Jev Group free/jev-1.13, POST /v1/decisions) pick the right element on an
application page from browser-use's element list — the list that is very long when the browser is Obscura?

For each page (a local test form and real Greenhouse / Lever / Ashby application pages — filled, never submitted):
  1. the browser (Obscura or Chromium) opens it; browser-use reads it into its numbered element list
  2. ONE decision call asks, for each field the candidate must fill (name, email, phone, resume, submit button):
     "which element is it?" — a `choice` question over the element numbers, the list itself in `state`
  3. each pick is graded against what the page really is (ids, names, types, labels)
  4. on the local form the picks are then used: browser-use types / uploads into them and the form is submitted,
     and the server checks what arrived

The key is read from the file in $KEYVIX_KEY_FILE (never from the code or the command line).
Run from jobhunterx/:  KEYVIX_KEY_FILE=... python -m scripts.decision_picker_trial --obscura ./obscura [--json out]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.request

from scripts.browser_trial import PDF, REAL_PAGES, _Form, _port, start_browser

API = "https://api.keyvix.nl/v1/decisions"
MODEL = os.environ.get("DECISION_MODEL", "free/jev-1.13")
MIN_GAP_S = 13.0                                  # free tier: 5 calls a minute for the whole account

FIELDS = {
    "full_name": "the text box for the candidate's full name, or their FIRST name when first and last name are separate",
    "email": "the text box for the candidate's email address",
    "phone": "the text box for the candidate's phone number",
    "resume": "the file input (upload) for the RESUME / CV — not the cover letter and not an autofill helper",
    "submit": "the button that submits the whole application",
}


FORM_ONLY = False
MAX_STATE_CHARS = 180_000                         # ~45K tokens: inside jev's 64K context with the questions


def _is_control(n) -> bool:
    a = n.attributes or {}
    return n.tag_name in ("input", "textarea", "select", "button") or a.get("role") in (
        "button", "combobox", "checkbox", "radio", "textbox", "listbox")


def _attrs(n) -> dict:
    return {k: v for k, v in (n.attributes or {}).items() if v}


def _text(n) -> str:
    try:
        return re.sub(r"\s+", " ", n.get_all_children_text(max_depth=3) or "").strip()
    except Exception:
        return ""


def describe(idx: int, n) -> str:
    a = _attrs(n)
    keep = {k: a[k] for k in ("id", "name", "type", "placeholder", "aria-label", "autocomplete", "accept", "role",
                              "value", "title", "data-qa", "for") if k in a}
    bits = [f"[{idx}] <{n.tag_name}>"] + [f'{k}="{str(v)[:60]}"' for k, v in keep.items()]
    t = _text(n)
    if t:
        bits.append(f'text="{t[:80]}"')
    return " ".join(bits)


def truth(field: str, n, site: str) -> bool:
    """Is this element really the field? Judged from the page itself (ids, names, types, labels)."""
    a = {k: str(v).lower() for k, v in _attrs(n).items()}
    tag, t = n.tag_name, _text(n).lower()
    key = " ".join([a.get("id", ""), a.get("name", ""), a.get("autocomplete", ""), a.get("aria-label", ""),
                    a.get("placeholder", ""), a.get("data-qa", "")])
    if field == "full_name":
        return tag == "input" and a.get("type", "text") in ("text", "") and bool(
            re.search(r"(^|[_\s-])(first[_\s-]?name|given-name|full[_\s-]?name|name|_systemfield_name)($|[_\s-])", key)) \
            and not re.search(r"last|family|company|org|preferred|middle", key)
    if field == "email":
        return tag == "input" and (a.get("type") == "email" or "email" in key)
    if field == "phone":
        return tag == "input" and (a.get("type") == "tel" or "phone" in key)
    if field == "resume":
        if not (tag == "input" and a.get("type") == "file"):
            return False
        if re.search(r"cover|autofill", key):
            return False
        return bool(re.search(r"resume|cv", key)) or site in ("local",)
    if field == "submit":
        return tag in ("button", "input") and ("submit" in t or "submit" in a.get("value", "") or a.get("type") == "submit"
                                               and "apply" in (t + a.get("value", "")))
    return False


_last_call = [0.0]


def decide(state: str, options: dict[str, str], key: str) -> tuple[dict, float, dict]:
    wait = MIN_GAP_S - (time.monotonic() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    body = {"model": MODEL, "state": state, "questions": {
        f: {"type": "choice", "instructions": f"Which element is {desc}?", "criteria": options} for f, desc in FIELDS.items()}}
    for attempt in range(6):
        _last_call[0] = time.monotonic()
        t0 = time.monotonic()
        req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=90).read())
            return d, round(time.monotonic() - t0, 2), {"attempts": attempt + 1}
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:200]
            if e.code in (429, 503) and attempt < 5:
                time.sleep(15 if e.code == 429 else 30)
                continue
            return {"error": e.code, "message": msg}, round(time.monotonic() - t0, 2), {"attempts": attempt + 1}
    return {"error": "gave up"}, 0.0, {}


async def run(kind: str, obscura: str, key: str, sites: list[str]) -> dict:
    import http.server
    import threading

    from browser_use import BrowserProfile, BrowserSession
    from browser_use.browser.events import TypeTextEvent, UploadFileEvent

    proc, ws, port, _ = start_browser(kind, obscura, True)
    fport = _port()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", fport), _Form)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    pages = {"local": f"http://127.0.0.1:{fport}/", **{s: REAL_PAGES[s][0] for s in REAL_PAGES}}
    resume = os.path.join(tempfile.mkdtemp(), "Asha_Rao_Resume.pdf")
    open(resume, "wb").write(PDF)
    out = {"browser": kind, "model": MODEL, "pages": {}}
    bs = BrowserSession(browser_profile=BrowserProfile(cdp_url=ws if kind == "obscura" else f"http://127.0.0.1:{port}",
                                                       keep_alive=True))
    await bs.start()
    try:
        for site in sites:
            res: dict = {}
            out["pages"][site] = res
            try:
                await bs.navigate_to(pages[site])
                await asyncio.sleep(4 if site != "local" else 1)
                st = await bs.get_browser_state_summary(include_screenshot=False)
                sm_all = st.dom_state.selector_map
                res["elements"] = len(sm_all)
                # what the decision model chooses from: every element (when it fits its 64K context) or, with
                # --form-only, just the form controls — inputs, text areas, dropdowns and buttons
                sm = {i: n for i, n in sm_all.items() if not FORM_ONLY or _is_control(n)}
                res["choices_given"] = len(sm)
                lines = [describe(i, n) for i, n in sm.items()]
                state = ("A job application web page. Its interactive elements, one per line "
                         "(number, tag, attributes, visible text):\n" + "\n".join(lines))
                res["state_chars"] = len(state)
                if len(state) > MAX_STATE_CHARS:
                    res["error"] = f"element list too long for the decision model ({len(state):,} characters, ~{len(state)//4:,} tokens; limit 64K tokens)"
                    continue
                options = {f"e{i}": f"element [{i}]" for i in sm}
                answers, secs, meta = decide(state, options, key)
                res["decision_s"] = secs
                res.update(meta)
                if "answers" not in answers:
                    res["error"] = answers
                    continue
                res["usage"] = answers.get("usage")
                graded = {}
                for f in FIELDS:
                    a = answers["answers"].get(f, {})
                    pick = a.get("choice")
                    idx = int(pick[1:]) if isinstance(pick, str) and pick[1:].isdigit() else None
                    node = sm.get(idx) if idx is not None else None
                    exists = any(truth(f, n, site) for n in sm.values())
                    graded[f] = {"picked": describe(idx, node) if node is not None else pick,
                                 "confidence": a.get("confidence"),
                                 "correct": bool(node is not None and truth(f, node, site)),
                                 "field_exists_on_page": exists}
                res["picks"] = graded
                scored = [g for g in graded.values() if g["field_exists_on_page"]]
                res["accuracy"] = f"{sum(g['correct'] for g in scored)}/{len(scored)}"
                if site == "local":                       # use the picks for real and submit
                    _Form.got = {}

                    def node_of(f):
                        c = answers["answers"][f].get("choice", "")
                        return sm.get(int(c[1:])) if c[1:].isdigit() else None
                    for f, val in (("full_name", "Asha Rao"), ("email", "asha@example.com")):
                        if node_of(f) is not None:
                            ev = bs.event_bus.dispatch(TypeTextEvent(node=node_of(f), text=val))
                            await ev
                    if node_of("resume") is not None:
                        ev = bs.event_bus.dispatch(UploadFileEvent(node=node_of("resume"), file_path=resume))
                        await ev
                    cdp = await bs.get_or_create_cdp_session()
                    await cdp.cdp_client.send.Runtime.evaluate(params={"expression": "document.getElementById('years').value='0-1';"
                                                               "document.querySelector('[name=mode]').checked=true;"
                                                               "document.getElementById('consent').checked=true;"
                                                               "document.getElementById('go').click()"},
                                                               session_id=cdp.session_id)
                    await asyncio.sleep(2)
                    g = _Form.got
                    res["submitted_values"] = {"name": g.get("name"), "email": g.get("email"),
                                               "resume_bytes": (g.get("resume") or {}).get("bytes") if isinstance(g.get("resume"), dict) else None}
            except Exception as exc:
                res["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
    finally:
        try:
            await bs.kill()
        except Exception:
            pass
        proc.terminate()
        srv.shutdown()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--obscura", required=True)
    ap.add_argument("--only", default="obscura,chromium")
    ap.add_argument("--sites", default="local,greenhouse,lever,ashby")
    ap.add_argument("--json", default="")
    ap.add_argument("--form-only", action="store_true", help="give the model only form controls to choose from")
    args = ap.parse_args()
    global FORM_ONLY
    FORM_ONLY = args.form_only
    key = open(os.environ["KEYVIX_KEY_FILE"]).read().strip()
    results = [asyncio.run(run(k, args.obscura, key, args.sites.split(","))) for k in args.only.split(",")]
    text = json.dumps(results, indent=2, default=str)
    print(text)
    if args.json:
        open(args.json, "w").write(text)


if __name__ == "__main__":
    main()
