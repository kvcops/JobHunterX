"""Application forms embedded from another site (an iframe on the company's careers page) with a shadow-DOM resume
widget and an Attach-button-only upload: pre-fill, uploads and the required-fields check must reach them, in Chromium,
and the server must receive the files."""

import asyncio
import glob
import http.server
import os
import socket
import subprocess
import tempfile
import threading
import time
import urllib.request

import pytest

PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"
CHROME = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux*/chrome")) or sorted(
    glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome")))
pytestmark = pytest.mark.skipif(not CHROME, reason="needs a Chromium build")


def _chrome():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    proc = subprocess.Popen([CHROME[-1], "--headless=new", f"--remote-debugging-port={p}", "--no-sandbox",
                             f"--user-data-dir={tempfile.mkdtemp()}", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{p}/json/version", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    return proc, p


got = {}
def port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p
FP = port(); MP = port()
FORM = """<!doctype html><html><body><h2>Apply</h2>
<form id=f>
<label for=fn>First Name *</label><input id=fn name=first_name required>
<label for=ln>Last Name *</label><input id=ln name=last_name required>
<label for=em>Email *</label><input id=em name=email type=email required>
<label for=ph>Phone *</label><input id=ph name=phone required>
<label for=li>LinkedIn Profile</label><input id=li name=linkedin>
<label for=q1>Why us? *</label><textarea id=q1 name=why required></textarea>
<div><span>Resume/CV *</span><resume-widget></resume-widget></div>
<div><span>Cover Letter</span><button type=button id=attach>Attach</button><span id=cl>none</span></div>
<button type=submit>Submit application</button></form>
<script>
customElements.define('resume-widget', class extends HTMLElement { constructor(){ super();
  const r = this.attachShadow({mode:'open'});
  r.innerHTML = '<div class=drop>Drop your resume or <label>browse<input type=file accept=".pdf" required style="display:none"></label></div>'; } });
let coverFile = null;
document.getElementById('attach').onclick = () => { const i = document.createElement('input'); i.type = 'file';
  i.onchange = () => { coverFile = i.files[0]; document.getElementById('cl').textContent = coverFile.name; }; i.click(); };
document.getElementById('f').onsubmit = async (e) => { e.preventDefault();
  const fd = new FormData(document.getElementById('f'));
  const rf = document.querySelector('resume-widget').shadowRoot.querySelector('input[type=file]').files[0];
  if (rf) fd.append('resume', rf); if (coverFile) fd.append('cover', coverFile);
  await fetch('/submit', {method:'POST', body: fd}); document.body.insertAdjacentHTML('beforeend','<p id=ok>Thanks</p>'); };
</script></body></html>"""
MAIN = f"""<!doctype html><html><body><h1>Careers at Acme</h1>
<iframe id=gh src="http://localhost:{FP}/form" style="width:900px;height:900px"></iframe></body></html>"""
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        b = (FORM if self.path.startswith('/form') else MAIN).encode()
        self.send_response(200); self.send_header('Content-Type','text/html'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        raw = self.rfile.read(int(self.headers['Content-Length']))
        got['bytes'] = len(raw); got['resume'] = b'name="resume"' in raw and PDF[:8] in raw; got['cover'] = b'name="cover"' in raw
        got['first'] = b'Vamsi' in raw; got['phone'] = b'8074749058' in raw
        self.send_response(200); self.send_header('Content-Length','0'); self.end_headers()
for p in (FP, MP):
    threading.Thread(target=http.server.ThreadingHTTPServer(("127.0.0.1", p), H).serve_forever, daemon=True).start()



def test_embedded_cross_site_form_gets_filled_and_both_files_arrive():
    from browser_use import BrowserProfile, BrowserSession

    from jobhunterx.agents import browser_agent as ba
    from jobhunterx.agents import form_frames as ff

    async def main():
        proc, cport = _chrome()
        d = tempfile.mkdtemp(); res = os.path.join(d, "Resume.pdf"); cov = os.path.join(d, "Cover.pdf")
        open(res, "wb").write(PDF); open(cov, "wb").write(PDF)
        bs = BrowserSession(browser_profile=BrowserProfile(cdp_url=f"http://127.0.0.1:{cport}", keep_alive=True))
        await bs.start()
        try:
            await bs.navigate_to(f"http://127.0.0.1:{MP}/")
            await asyncio.sleep(2)
            sessions = await ff.page_sessions(bs)
            assert len(sessions) >= 2                                  # the page + the form's own (cross-site) frame
            profile = {"name": "Vamsi Krishna Karri", "email": "vamsikv28@gmail.com", "phone": "+91 80747 49058",
                       "linkedin": "https://www.linkedin.com/in/x", "preferences": {"home_country": "India"}}
            r = await ba._prefill(bs, profile)
            assert "First Name = Vamsi Krishna" in r.extracted_content and "+91 8074749058" in r.extracted_content
            assert set(await ff.empty_required(bs)) == {"Why us? *", "browse (file)"}
            ok, _ = await ff.upload_document(bs, "resume", res)
            assert ok                                                  # inside the shadow-DOM widget
            ok, msg = await ff.upload_document(bs, "cover_letter", cov)
            assert not ok and "no cover letter upload field" in msg   # never into the resume field

            async def press():
                for sid in sessions[1:]:
                    await bs.cdp_client.send.Runtime.evaluate(
                        params={"expression": "document.getElementById('attach').click()", "userGesture": True}, session_id=sid)
            ok, _ = await ff.upload_via_chooser(bs, press, cov)
            assert ok                                                  # the Attach button's file chooser
            for sid in sessions[1:]:
                await bs.cdp_client.send.Runtime.evaluate(params={"expression": "document.getElementById('q1').value='Great team'"}, session_id=sid)
            assert await ff.empty_required(bs) == []
            for sid in sessions[1:]:
                await bs.cdp_client.send.Runtime.evaluate(params={"expression": "document.querySelector('button[type=submit]').click()"}, session_id=sid)
            await asyncio.sleep(1.5)
        finally:
            await bs.kill(); proc.terminate()

    asyncio.run(main())
    assert got.get("resume") and got.get("cover") and got.get("first") and got.get("phone")
