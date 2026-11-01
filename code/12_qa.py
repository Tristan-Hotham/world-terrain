"""QA: open index.html in Chromium (Playwright) at 1280 px and 390 px, record console errors and save screenshots to qa/.
The container cannot reach the live terrain tiles, so tile requests are answered from the local zoom 4 grid
(resampled for other zooms); Esri tiles and web fonts are not reachable either and are left blank.
Run: python3 code/12_qa.py
"""
import io, os, re, sys, threading, http.server, functools
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

E = np.load(f"{WORK}/elev.npy").astype(np.float64)
LEAF = os.environ.get("LEAFLET_DIST", "/tmp/claude-0/-home-claude/9791f396-0812-550b-8fd1-2ad33918f115/scratchpad/node_modules/leaflet/dist")
QA = os.path.join(ROOT, "qa"); os.makedirs(QA, exist_ok=True)


def tile(z, x, y):
    n = 2 ** z; f = N / (256 * n)
    jj = (y * 256 + np.arange(256) + .5) * f; ii = (x * 256 + np.arange(256) + .5) * f
    j0 = np.clip(np.floor(jj - .5).astype(int), 0, N - 2); i0 = np.floor(ii - .5).astype(int) % N
    ty = np.clip(jj - .5 - j0, 0, 1)[:, None]; tx = (ii - .5 - np.floor(ii - .5))[None, :]
    i1 = (i0 + 1) % N
    if f >= 1:
        k = int(f); a = E.reshape(N // k, k, N // k, k).mean(axis=(1, 3)) if k > 1 else E
        a = a[y * 256:(y + 1) * 256, x * 256:(x + 1) * 256]
    else:
        a = (E[j0][:, i0] * (1 - tx) + E[j0][:, i1] * tx) * (1 - ty) + (E[j0 + 1][:, i0] * (1 - tx) + E[j0 + 1][:, i1] * tx) * ty
    v = np.clip(a + 32768, 0, 65535.99); R_ = np.floor(v / 256); G = np.floor(v - R_ * 256); B = np.floor((v - R_ * 256 - G) * 256)
    b = io.BytesIO(); Image.fromarray(np.dstack([R_, G, B]).astype(np.uint8)).save(b, "PNG"); return b.getvalue()


def serve():
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
    h.log_message = lambda *a: None
    s = http.server.ThreadingHTTPServer(("127.0.0.1", 8839), h); threading.Thread(target=s.serve_forever, daemon=True).start(); return s


def route(r):
    u = r.request.url
    m = re.search(r"terrarium/(\d+)/(\d+)/(\d+)\.png", u)
    if m:
        return r.fulfill(status=200, body=tile(*map(int, m.groups())), headers={"Content-Type": "image/png", "Access-Control-Allow-Origin": "*"})
    if "cdnjs.cloudflare.com" in u and "leaflet" in u:      # the CDN is not reachable from the container: serve a local copy
        f = "leaflet.css" if u.endswith(".css") else "leaflet.js"
        return r.fulfill(status=200, body=open(os.path.join(LEAF, f), "rb").read(), headers={"Content-Type": "text/css" if f.endswith("css") else "application/javascript"})
    if u.startswith("http://127.0.0.1"):
        return r.continue_()
    return r.abort()


if __name__ == "__main__":
    srv = serve()
    errs = []; netfail = []
    with sync_playwright() as p:
        br = p.chromium.launch()
        for name, vw, vh in (("desktop", 1280, 900), ("phone", 390, 844)):
            pg = br.new_page(viewport={"width": vw, "height": vh}, device_scale_factor=1 if vw > 500 else 2)
            pg.on("console", lambda m, n=name: errs.append((n, m.type, m.text)) if m.type == "error" else None)
            pg.on("pageerror", lambda e, n=name: errs.append((n, "pageerror", str(e))))
            pg.on("framenavigated", lambda f, n=name: print(n, "navigated", f.url) if f == pg.main_frame else None)
            pg.on("requestfailed", lambda q, n=name: netfail.append(q.url))
            pg.route("**/*", route)
            pg.goto("http://127.0.0.1:8839/index.html", wait_until="load")
            pg.wait_for_timeout(4500)
            pg.screenshot(path=f"{QA}/{name}_top.png")
            pg.locator("#atlas").scroll_into_view_if_needed(); pg.wait_for_timeout(2500)
            pg.screenshot(path=f"{QA}/{name}_map.png")
            box = pg.locator("#lmap").bounding_box()
            pg.mouse.click(box["x"] + box["width"] * .68, box["y"] + box["height"] * .42); pg.wait_for_timeout(2000)
            pg.screenshot(path=f"{QA}/{name}_click.png")
            pg.evaluate("map.setView([29.5, 85], 6); 0"); pg.wait_for_timeout(3500)
            pg.locator("#lmap").screenshot(path=f"{QA}/{name}_himalaya.png")
            pg.evaluate("setStyle('band'); map.setView([46.3, 9], 6); 0"); pg.wait_for_timeout(3000)
            pg.locator("#lmap").screenshot(path=f"{QA}/{name}_alps_bands.png")
            pg.evaluate("setStyle('shade'); setCities(true); map.setView([-16, -68], 5); 0"); pg.wait_for_timeout(3000)
            pg.locator("#lmap").screenshot(path=f"{QA}/{name}_andes_shade.png")
            pg.evaluate("setStyle('both'); setCities(false); map.setView([28, 15], 2); 0"); pg.wait_for_timeout(1500)
            for sec in ("hypsChart", "contChart", "promChart", "bandChart", "belowChart"):
                pg.locator("#" + sec).scroll_into_view_if_needed(); pg.wait_for_timeout(400)
                pg.locator("#" + sec).screenshot(path=f"{QA}/{name}_{sec}.png")
            w = pg.evaluate("document.documentElement.scrollWidth")
            print(name, "scrollWidth", w)
            pg.screenshot(path=f"{QA}/{name}_full.png", full_page=True)
            pg.close()
        br.close()
    srv.shutdown()
    real = [e for e in errs if "Failed to load resource" not in e[2]]
    print("blocked requests (Esri tiles, web fonts; expected in the container):", len(netfail), sorted({re.sub(r"/tile/.*", "/tile/...", u.split("?")[0]) for u in netfail})[:6])
    print("console errors other than blocked requests:", real if real else "none")
