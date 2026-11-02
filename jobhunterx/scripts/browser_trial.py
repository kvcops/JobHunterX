"""Side-by-side trial: Obscura (https://github.com/h4ckf0r0day/obscura) vs headless Chromium, as the browser behind
JobHunterX's auto-apply agent. Both are driven the way the app drives a browser — over CDP (BROWSER_CDP_URL) — and
measured on the same tasks:

  1. a local application form: text, select, radio, checkbox, a field that appears by JS, a resume file upload, submit
     (the server checks every value and the uploaded bytes)
  2. real application pages (Greenhouse, Lever, Ashby): load, find the name field and the resume upload, fill them —
     never submitted
  3. a public bot-check page (bot.sannysoft.com)
  4. the CDP features the app's live view and "take over" use: screencast frames, mouse input, screenshot
  5. browser-use (the agent library): read the page into the element list the AI sees, type into a field, upload
  6. memory (resident RAM of the browser's processes) and time for each step

Run from jobhunterx/:  python -m scripts.browser_trial --obscura /path/to/obscura [--json out.json]
"""

from __future__ import annotations

import argparse
import asyncio
import glob
import http.server
import io
import json
import os
import socket
import subprocess
import tempfile
import threading
import time
import urllib.request

import psutil

REAL_PAGES = {
    "greenhouse": ("https://job-boards.greenhouse.io/anthropic/jobs/5183044008",
                   'input#first_name, input[name="first_name"], input[autocomplete="given-name"]'),
    "lever": ("https://jobs.lever.co/palantir/6ed76ce8-4156-4b60-b120-403538bd66cd/apply", 'input[name="name"]'),
    "ashby": ("https://jobs.ashbyhq.com/openai/240d459b-696d-43eb-8497-fab3e56ecd9b/application",
              'input[name="_systemfield_name"], input#_systemfield_name'),
}

FORM = """<!doctype html><html><head><meta charset="utf-8"><title>Apply — Test Labs</title>
<style>body{font-family:sans-serif;max-width:640px;margin:40px auto} label{display:block;margin:10px 0}</style></head>
<body><h1>Apply: AI Engineer</h1>
<form id="f" method="post" action="/submit" enctype="multipart/form-data">
<label>Full name <input name="name" id="name" required></label>
<label>Email <input name="email" type="email" id="email" required></label>
<label>Years of experience <select name="years" id="years"><option value="">Pick</option><option>0-1</option><option>1-2</option><option>3+</option></select></label>
<fieldset><legend>Work mode</legend><label><input type="radio" name="mode" value="remote"> Remote</label>
<label><input type="radio" name="mode" value="onsite"> On-site</label></fieldset>
<label><input type="checkbox" name="consent" id="consent" value="yes"> I agree to the privacy notice</label>
<div id="extra"></div>
<label>Resume <input type="file" name="resume" id="resume" accept=".pdf"></label>
<button type="submit" id="go">Submit application</button>
</form>
<p id="clicked">not clicked</p><button id="probe" onclick="document.getElementById('clicked').textContent='clicked'">Probe</button>
<script>
document.getElementById('years').addEventListener('change', (e) => {
  const x = document.getElementById('extra');
  x.innerHTML = e.target.value === '1-2' ? '<label>Notice period <input name="notice" id="notice"></label>' : '';
});
</script></body></html>"""

SHOTS = os.environ.get("TRIAL_SHOTS", tempfile.gettempdir())
PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"


class _Form(http.server.BaseHTTPRequestHandler):
    got: dict = {}

    def log_message(self, *a):
        pass

    def do_GET(self):
        body = FORM.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path == "/upload-check":           # does the attached file's content really go out?
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            _Form.got = {"upload_bytes": len(raw), "pdf_in_request": PDF[:8] in raw}
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")
            return
        from email.parser import BytesParser
        from email.policy import default
        raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        msg = BytesParser(policy=default).parsebytes(
            f"Content-Type: {self.headers['Content-Type']}\r\n\r\n".encode() + raw)
        got = {}
        for part in msg.iter_parts():
            name = part.get_param("name", header="content-disposition")
            data = part.get_payload(decode=True) or b""
            fn = part.get_filename()
            got[name] = {"filename": fn, "bytes": len(data)} if fn else data.decode(errors="replace")
        _Form.got = got
        body = b"<html><body><h1 id='ok'>Thanks</h1></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _rss_mb(pid: int) -> float:
    try:
        p = psutil.Process(pid)
        procs = [p, *p.children(recursive=True)]
        # PSS: shared pages are split between the processes that share them (RSS would count Chromium's shared
        # libraries once per process and overstate it several times)
        total = 0
        for x in procs:
            try:
                total += x.memory_full_info().pss
            except psutil.Error:
                pass
        return round(total / 2**20, 1)
    except psutil.Error:
        return 0.0


def _wait_cdp(port: int, timeout: float = 30) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        try:
            return json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2).read())
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("CDP endpoint did not come up")


def start_browser(kind: str, obscura: str, stealth: bool) -> tuple[subprocess.Popen, str, int, float]:
    port = _port()
    t0 = time.monotonic()
    if kind == "obscura":
        cmd = [obscura, "serve", "--port", str(port), "--allow-private-network", "--allow-file-access", "--quiet"]
        if stealth:
            cmd.append("--stealth")
    else:
        chrome = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux*/chrome"))[-1]
        cmd = [chrome, "--headless=new", f"--remote-debugging-port={port}", "--no-sandbox", "--no-first-run",
               f"--user-data-dir={tempfile.mkdtemp(prefix='trial-chrome-')}", "--window-size=1280,900", "about:blank"]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    info = _wait_cdp(port)
    ws = info.get("webSocketDebuggerUrl") or f"ws://127.0.0.1:{port}/devtools/browser"
    return proc, ws, port, round(time.monotonic() - t0, 2)


async def run(kind: str, obscura: str, stealth: bool) -> dict:
    from playwright.async_api import async_playwright

    out: dict = {"browser": kind, "steps": {}, "ram_mb": {}}
    proc, ws, port, startup = start_browser(kind, obscura, stealth)
    out["startup_s"] = startup
    out["ram_mb"]["idle"] = _rss_mb(proc.pid)
    peak = [out["ram_mb"]["idle"]]
    stop = threading.Event()

    def sample():
        while not stop.is_set():
            peak.append(_rss_mb(proc.pid))
            time.sleep(0.25)

    threading.Thread(target=sample, daemon=True).start()
    fport = _port()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", fport), _Form)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    form_url = f"http://127.0.0.1:{fport}/"
    resume = os.path.join(tempfile.mkdtemp(), "Asha_Rao_Resume.pdf")
    open(resume, "wb").write(PDF)

    async def step(name, coro, timeout=60):
        t0 = time.monotonic()
        try:
            res = await asyncio.wait_for(coro, timeout)
            out["steps"][name] = {"ok": True, "s": round(time.monotonic() - t0, 2), **(res or {})}
        except Exception as exc:
            out["steps"][name] = {"ok": False, "s": round(time.monotonic() - t0, 2),
                                  "error": f"{type(exc).__name__}: {str(exc)[:220]}"}
        out["ram_mb"][name] = _rss_mb(proc.pid)

    try:
        async with async_playwright() as p:
            browser = None

            async def connect():
                nonlocal browser
                browser = await p.chromium.connect_over_cdp(ws if kind == "obscura" else f"http://127.0.0.1:{port}")
                return {}
            await step("connect (Playwright over CDP)", connect(), 30)
            if browser is None:
                return out
            ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await ctx.new_page()

            async def local_form():
                _Form.got = {}
                await page.goto(form_url, wait_until="load")
                await page.fill("#name", "Asha Rao")
                await page.fill("#email", "asha@example.com")
                await page.select_option("#years", "1-2")
                await page.wait_for_selector("#notice", timeout=5000)      # appears by JS after the select
                await page.fill("#notice", "30 days")
                await page.check('input[name="mode"][value="remote"]')
                await page.check("#consent")
                await page.set_input_files("#resume", resume)
                await page.click("#go")
                await page.wait_for_selector("#ok", timeout=10000)
                g = _Form.got
                want = {"name": "Asha Rao", "email": "asha@example.com", "years": "1-2", "notice": "30 days",
                        "mode": "remote", "consent": "yes"}
                wrong = {k: g.get(k) for k, v in want.items() if g.get(k) != v}
                up = g.get("resume") or {}
                return {"all_values_received": not wrong, "wrong": wrong,
                        "resume_uploaded": isinstance(up, dict) and up.get("bytes") == len(PDF)}
            await step("local form: fill + upload + submit", local_form())

            for site, (url, sel) in REAL_PAGES.items():
                async def real(url=url, sel=sel):
                    t0 = time.monotonic()
                    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    loaded = round(time.monotonic() - t0, 2)
                    found = True
                    try:
                        await page.wait_for_selector(sel, timeout=20000)
                    except Exception:
                        found = False
                    res = {"page_load_s": loaded, "name_field_found": found,
                           "inputs_on_page": await page.locator("input").count(),
                           "file_inputs": await page.locator('input[type="file"]').count()}
                    if found:
                        await page.fill(sel, "Asha Rao")
                        res["name_filled"] = (await page.locator(sel).first.input_value()) == "Asha Rao"
                    if res["file_inputs"]:
                        try:
                            await page.locator('input[type="file"]').first.set_input_files(resume)
                            res["resume_attached"] = await page.evaluate(
                                "() => { const f = document.querySelector('input[type=file]'); return !!(f && f.files && f.files.length) }")
                        except Exception as exc:
                            res["resume_attached"] = f"error: {str(exc)[:80]}"
                    return res
                await step(f"real page: {site}", real(), 80)

            async def botcheck():
                await page.goto("https://bot.sannysoft.com/", wait_until="load", timeout=45000)
                await page.wait_for_timeout(2500)
                r = await page.evaluate("""() => {
                  const cells = [...document.querySelectorAll('td')];
                  const failed = cells.filter(c => /failed/i.test(c.className) || /^\\s*FAIL/i.test(c.textContent)).length;
                  const passed = cells.filter(c => /passed/i.test(c.className)).length;
                  return {failed, passed, webdriver: navigator.webdriver, ua: navigator.userAgent,
                          plugins: navigator.plugins ? navigator.plugins.length : -1, languages: navigator.languages};
                }""")
                return r
            await step("bot check (bot.sannysoft.com)", botcheck(), 70)

            async def cdp_features():
                await page.goto(form_url, wait_until="load")
                cdp = await ctx.new_cdp_session(page)
                res = {}
                frames = []
                cdp.on("Page.screencastFrame", lambda e: (frames.append(1), asyncio.ensure_future(
                    cdp.send("Page.screencastFrameAck", {"sessionId": e["sessionId"]}))))
                try:
                    await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 60, "everyNthFrame": 1})
                    for i in range(6):
                        await page.evaluate(f"document.getElementById('clicked').textContent = 'tick {i}'")
                        await asyncio.sleep(0.4)
                    await cdp.send("Page.stopScreencast")
                    res["live_view_frames_in_2.4s"] = len(frames)
                except Exception as exc:
                    res["live_view"] = f"error: {str(exc)[:120]}"
                try:
                    box = await page.locator("#probe").bounding_box()
                    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
                    for t in ("mousePressed", "mouseReleased"):
                        await cdp.send("Input.dispatchMouseEvent", {"type": t, "x": x, "y": y, "button": "left", "clickCount": 1})
                    res["take_over_click_works"] = (await page.text_content("#clicked")) == "clicked"
                except Exception as exc:
                    res["take_over_click_works"] = f"error: {str(exc)[:120]}"
                try:
                    await page.click("#name")
                    await cdp.send("Input.insertText", {"text": "typed by you"})
                    res["take_over_typing_works"] = (await page.input_value("#name")) == "typed by you"
                except Exception as exc:
                    res["take_over_typing_works"] = f"error: {str(exc)[:120]}"
                try:
                    shot = await page.screenshot()
                    res["screenshot_kb"] = round(len(shot) / 1024, 1)
                except Exception as exc:
                    res["screenshot"] = f"error: {str(exc)[:120]}"
                return res
            await step("live view + take over (CDP)", cdp_features(), 60)

            async def resume_really_sent():
                """Attach the resume the way browser-use does (DOM.setFileInputFiles), send the form with fetch +
                FormData (how React application forms send) and check the PDF bytes arrive at the server."""
                _Form.got = {}
                await page.goto(form_url, wait_until="load")
                cdp = await ctx.new_cdp_session(page)
                doc = await cdp.send("DOM.getDocument", {"depth": -1})
                node = await cdp.send("DOM.querySelector", {"nodeId": doc["root"]["nodeId"], "selector": "#resume"})
                await cdp.send("DOM.setFileInputFiles", {"files": [resume], "nodeId": node["nodeId"]})
                shown = await page.evaluate("""async () => { const i = document.getElementById('resume');
                    await fetch('/upload-check', {method: 'POST', body: new FormData(document.getElementById('f'))});
                    return i.files ? i.files.length : 0 }""")
                await page.wait_for_timeout(500)
                return {"page_shows_file_attached": shown == 1, **_Form.got}
            await step("resume really sent (fetch + FormData)", resume_really_sent(), 30)
            await browser.close()
    finally:
        pass

    async def agent_library():
        """What the agent itself does each step: read the page into the numbered element list the AI picks from,
        then type into a field and attach the resume through browser-use's own actions."""
        from browser_use import BrowserProfile, BrowserSession
        from browser_use.browser.events import TypeTextEvent, UploadFileEvent
        bs = BrowserSession(browser_profile=BrowserProfile(cdp_url=ws if kind == "obscura" else f"http://127.0.0.1:{port}",
                                                           keep_alive=True))
        await bs.start()
        try:
            await bs.navigate_to(form_url)
            await asyncio.sleep(1)
            t0 = time.monotonic()
            state = await bs.get_browser_state_summary(include_screenshot=True)
            read_s = round(time.monotonic() - t0, 2)
            sm = state.dom_state.selector_map
            res = {"page_read_s": read_s, "elements_ai_can_use": len(sm), "screenshot_for_ai": bool(state.screenshot)}
            name_node = next((n for n in sm.values() if (n.attributes or {}).get("id") == "name"), None)
            file_node = next((n for n in sm.values() if (n.attributes or {}).get("type") == "file"), None)
            if name_node is not None:
                ev = bs.event_bus.dispatch(TypeTextEvent(node=name_node, text="Asha Rao"))
                await ev
                await ev.event_result(raise_if_any=True, raise_if_none=False)
                cdp = await bs.get_or_create_cdp_session()
                v = await cdp.cdp_client.send.Runtime.evaluate(params={"expression": "document.getElementById('name').value",
                                                                       "returnByValue": True}, session_id=cdp.session_id)
                res["agent_typed"] = v.get("result", {}).get("value") == "Asha Rao"
            else:
                res["agent_typed"] = "name field not in the element list"
            if file_node is not None:
                ev = bs.event_bus.dispatch(UploadFileEvent(node=file_node, file_path=resume))
                await ev
                await ev.event_result(raise_if_any=True, raise_if_none=False)
                cdp = await bs.get_or_create_cdp_session()
                v = await cdp.cdp_client.send.Runtime.evaluate(params={"expression": "document.getElementById('resume').files.length",
                                                                       "returnByValue": True}, session_id=cdp.session_id)
                res["agent_uploaded"] = v.get("result", {}).get("value") == 1
            else:
                res["agent_uploaded"] = "file input not in the element list"
            for site in ("greenhouse", "ashby"):
                await bs.navigate_to(REAL_PAGES[site][0])
                await asyncio.sleep(4)
                t0 = time.monotonic()
                st = await bs.get_browser_state_summary(include_screenshot=True)
                res[f"{site}_read_s"] = round(time.monotonic() - t0, 2)
                res[f"{site}_elements_ai_can_use"] = len(st.dom_state.selector_map)
                if st.screenshot:
                    import base64
                    open(os.path.join(SHOTS, f"{kind}_{site}.png"), "wb").write(base64.b64decode(st.screenshot))
            return res
        finally:
            try:
                await bs.kill()
            except Exception:
                pass

    await step("browser-use agent: read page, type, upload", agent_library(), 90)
    stop.set()
    out["ram_mb"]["peak"] = max(peak)
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    srv.shutdown()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--obscura", required=True)
    ap.add_argument("--json", default="")
    ap.add_argument("--only", default="obscura,chromium")
    ap.add_argument("--no-stealth", action="store_true")
    args = ap.parse_args()
    results = [asyncio.run(run(k, args.obscura, not args.no_stealth)) for k in args.only.split(",")]
    text = json.dumps(results, indent=2, default=str)
    print(text)
    if args.json:
        open(args.json, "w").write(text)


if __name__ == "__main__":
    main()
