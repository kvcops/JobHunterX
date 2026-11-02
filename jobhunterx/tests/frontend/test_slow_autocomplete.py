"""A city field that suggests places as you type: it waits after the last key, says "No results" meanwhile, answers
slowly, matches only the place's own name, and draws its list inside a shadow root. choose_option must wait for the
real answer and pick the right place."""

import asyncio
import http.server
import os
import threading

import pytest

from tests.frontend.test_embedded_forms import CHROME, _chrome, port

pytestmark = pytest.mark.skipif(not CHROME, reason="needs a Chromium build")

PAGE = """<!doctype html><html><body><h2>Apply</h2>
<label for=city>Location (City) *</label><input id=city role=combobox aria-autocomplete=list autocomplete=off>
<city-list></city-list>
<script>
const PLACES = ['Hyderabad, Sindh, Pakistan', 'Hyderabad, Telangana, India', 'Hyderabad Road, Kent, UK', 'Pune, Maharashtra, India'];
customElements.define('city-list', class extends HTMLElement { constructor(){ super(); this.attachShadow({mode:'open'}); } });
const box = document.querySelector('city-list').shadowRoot, inp = document.getElementById('city');
let timer = null;
const draw = (items) => { box.innerHTML = items.length
  ? '<ul role=listbox>' + items.map((p) => '<li role=option>' + p + '</li>').join('') + '</ul>'
  : '<div class=empty>No results found</div>';
  for (const li of box.querySelectorAll('li')) li.onmousedown = (e) => { e.preventDefault(); inp.value = li.textContent; box.innerHTML = ''; }; };
inp.addEventListener('input', () => { clearTimeout(timer); draw([]);           // "No results" while the user types
  const q = inp.value.trim().toLowerCase();
  timer = setTimeout(() => setTimeout(() =>                                  // 0.5 s pause, then a 2.5 s server
    draw(q.length < 2 ? [] : PLACES.filter((p) => p.toLowerCase().startsWith(q))), 2500), 500); });
</script></body></html>"""

PP = port()


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        b = PAGE.encode()
        self.send_response(200); self.send_header('Content-Type', 'text/html'); self.send_header('Content-Length', str(len(b)))
        self.end_headers(); self.wfile.write(b)


threading.Thread(target=http.server.ThreadingHTTPServer(("127.0.0.1", PP), H).serve_forever, daemon=True).start()


def test_slow_city_suggestions_are_waited_for_and_the_right_place_chosen():
    from browser_use import BrowserProfile, BrowserSession

    from jobhunterx.agents import browser_agent as ba

    async def main():
        proc, cport = _chrome()
        bs = BrowserSession(browser_profile=BrowserProfile(cdp_url=f"http://127.0.0.1:{cport}", keep_alive=True))
        await bs.start()
        try:
            await bs.navigate_to(f"http://127.0.0.1:{PP}/")
            await asyncio.sleep(1.5)
            await bs.get_browser_state_summary()
            idx = next(i for i, n in (await bs.get_selector_map()).items() if (n.attributes or {}).get("id") == "city")
            r = await ba._choose_option(bs, idx, "Hyderabad, Telangana, India")
            assert r.error is None, r.error
            assert "Hyderabad, Telangana, India" in r.extracted_content
            val = await bs.cdp_client.send.Runtime.evaluate(params={"expression": "document.getElementById('city').value",
                                                                    "returnByValue": True},
                                                            session_id=(await bs.get_or_create_cdp_session()).session_id)
            return val["result"]["value"]
        finally:
            await bs.kill(); proc.terminate()

    assert asyncio.run(main()) == "Hyderabad, Telangana, India"
