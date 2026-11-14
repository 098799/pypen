"""The picture viewer (the kit's, KIT-VIEWER, bundled in /kit/shell.js) on
pypen's pages, in a real browser.

Headless Chromium at 390×844 (touch) against a throwaway copy of the local
database, with made-up photos in a temp media folder: never the live data on
bae, never the local db.sqlite3 itself. Shares layer_probe's start-up.

It walks the wiring, not the kit's gestures (the kit's own test does those):
the big photo opens the thumbs' set at the chosen one (next UI: aria-current,
the old pages: .active), a thumb still swaps the big photo, the viewer opens
the 1200 px copy and the stored file only when zoomed, samples and swatches
open, Back and Esc close, an htmx swap keeps it working, and the Gantt's zoom
chips are no pictures.

    python3 tools/viewer_probe.py                  # playwright on the system python
    SHOTS=/some/dir python3 tools/viewer_probe.py  # also keep screenshots
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layer_probe as lp  # noqa: E402

lp.PORT = int(os.environ.get("PROBE_PORT", "18492"))
lp.BASE = BASE = f"http://127.0.0.1:{lp.PORT}"
check, failures = lp.check, lp.failures
SHOTS = os.environ.get("SHOTS")
# A worktree has no db.sqlite3 of its own (gitignored): the live checkout's copy.
DB = lp.APP / "db.sqlite3"
if not DB.exists():
    DB = Path("/home/tgrining/pypen/dpypen/db.sqlite3")

SEED = r"""
import django; django.setup()
from io import BytesIO
from PIL import Image, ImageDraw
from django.core.files.base import ContentFile
from dpypen.items.models import Pen, Usage, WritingSample, InkSwatch, PenPhoto

def pic(w, h, colour, label):
    im = Image.new("RGB", (w, h), colour)
    d = ImageDraw.Draw(im)
    for x in range(0, w, 80):
        d.line([(x, 0), (x, h)], fill=(255, 255, 255), width=2)
    d.rectangle([w // 3, h // 3, 2 * w // 3, 2 * h // 3], outline=(0, 0, 0), width=12)
    d.text((40, 40), label, fill=(0, 0, 0))
    b = BytesIO(); im.save(b, "JPEG", quality=80)
    return ContentFile(b.getvalue(), name=label + ".jpg")

u = Usage.objects.select_related("pen", "ink").order_by("-begin").first()
pen, ink = u.pen, u.ink
pen.photos.all().delete()
# six: a strip of five or more thumbs once pushed the page past a phone's edge
for i, c in enumerate([(176, 120, 60), (60, 90, 150), (90, 140, 80), (150, 60, 90), (120, 120, 120), (200, 180, 90)]):
    PenPhoto(pen=pen, image=pic(2400, 1600, c, f"photo{i}"), position=i,
             kind=["main", "nib", "capped", "other", "other", "other"][i]).save()
WritingSample(usage=u, image=pic(1600, 1200, (230, 220, 200), "sample0"), notes="loops").save()
WritingSample(usage=u, image=pic(1600, 1200, (220, 230, 210), "sample1")).save()
InkSwatch(ink=ink, image=pic(1200, 1200, (40, 60, 160), "swatch0")).save()
print(pen.pk, ink.pk)
"""


def seed(tmp):
    env = dict(os.environ, DJANGO_SETTINGS_MODULE="probe_settings", DEBUG="True", SECRET_KEY="probe-not-a-secret", PYTHONPATH=f"{tmp}:{lp.APP}")
    out = subprocess.run([str(lp.PY), "-c", SEED], cwd=lp.APP, env=env, capture_output=True, text=True, check=True).stdout.split()
    return int(out[-2]), int(out[-1])


def st(page):
    return page.evaluate("""() => { const d = document.getElementById('kit-viewer');
      const v = window.kitViewer && kitViewer.current();
      const img = v ? v.over.parentNode.querySelector('img') : null;
      return { open: !!(d && d.open), lock: document.documentElement.classList.contains('scroll-lock'),
               n: d ? d.querySelector('.kv-n').textContent : '', cap: d ? d.querySelector('.kv-cap').textContent : '',
               index: v ? v.index : -1, count: v ? v.items.length : 0,
               zoomed: !!(d && d.classList.contains('kv-zoomed')),
               src: img ? (img.getAttribute('src') || '') : '', alt: img ? img.alt : '',
               w: img ? img.getBoundingClientRect().width : 0, url: location.pathname } }""")


def shot(page, name):
    if SHOTS:
        page.screenshot(path=str(Path(SHOTS) / name))


def wait_open(page):
    page.wait_for_function("document.getElementById('kit-viewer') && document.getElementById('kit-viewer').open")
    page.wait_for_timeout(450)


def wait_closed(page):
    page.wait_for_function("!(document.getElementById('kit-viewer') && document.getElementById('kit-viewer').open)")
    page.wait_for_timeout(300)


def pen_page(page, pen, base, thumbs, mark):
    """The big photo and its thumbs, on the next UI (base '') or the old one ('/prev')."""
    page.goto(f"{BASE}{base}/pens/{pen}/")
    page.wait_for_load_state("networkidle")
    where = base or "next"
    check(f"{where}: the page is no wider than the phone", page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
    drawn = page.evaluate("(() => { const i = document.getElementById('photoImg'); return [i.currentSrc, i.naturalWidth]; })()")
    check(f"{where}: the page draws the 1200 px copy", "/media/sized/1200/" in drawn[0] and drawn[1] == 1200)
    check(f"{where}: the photo is a button for a keyboard", page.get_attribute("#photoImg", "role") == "button")

    page.click("#photoImg")
    wait_open(page)
    s = st(page)
    check(f"{where}: tap the photo: the viewer opens on 1 of 6", s["open"] and s["n"] == "1 of 6")
    check(f"{where}: the page under it is locked", s["lock"])
    check(f"{where}: it shows the 1200 px copy, fitted to the width", "/media/sized/1200/" in s["src"] and 380 <= s["w"] <= 391)
    check(f"{where}: the picture's alt is the caption", s["alt"] and s["alt"] == s["cap"] and "uncapped" in s["cap"].lower())
    if not base:
        shot(page, "viewer-open.png")
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(450)
    s = st(page)
    check(f"{where}: → walks to the next photo", s["n"] == "2 of 6" and "nib" in s["cap"].lower())
    page.evaluate("kitViewer.current().zoom(3)")
    sharp = False
    for _ in range(40):  # page.wait_for_function's polling is an eval, which the CSP refuses
        sharp = page.evaluate("""() => { const v = kitViewer.current(); const i = v && v.over.parentNode.querySelector('img');
            return !!i && i.naturalWidth > 1200; }""")  # the stored file (1800 px; fetched to a blob: url)
        if sharp:
            break
        page.wait_for_timeout(200)
    check(f"{where}: zoomed in, the stored file replaces the copy", sharp)
    check(f"{where}: and it says so", st(page)["zoomed"])
    if not base:
        shot(page, "viewer-zoomed.png")
    page.go_back()
    wait_closed(page)
    s = st(page)
    check(f"{where}: Back closes the viewer and stays on the pen", not s["open"] and s["url"] == f"{base}/pens/{pen}/")
    check(f"{where}: the lock is gone", not s["lock"])

    # a thumb swaps the big photo (the viewer leaves its tap alone), then the big photo opens at it
    third = page.locator(f"{thumbs} a[data-thumb]").nth(2)
    third.click()
    page.wait_for_timeout(300)
    check(f"{where}: a thumb does not open the viewer, nor leave the page", not st(page)["open"] and page.url.endswith(f"{base}/pens/{pen}/"))
    check(f"{where}: the chosen thumb is marked", third.evaluate(f"a => a.{mark}"))
    check(
        f"{where}: the big photo shows it",
        page.get_attribute("#photoImg", "src") == third.get_attribute("data-view"),
    )
    page.click("#photoImg")
    wait_open(page)
    check(f"{where}: the photo opens at the thumb chosen", st(page)["n"] == "3 of 6")
    page.click("#kit-viewer .kv-x")
    wait_closed(page)
    check(f"{where}: ✕ closes", not st(page)["open"] and page.url.endswith(f"{base}/pens/{pen}/"))

    # samples on the pen page
    page.locator("img[data-view-group=samples]").first.scroll_into_view_if_needed()
    page.locator("img[data-view-group=samples]").first.click()
    wait_open(page)
    s = st(page)
    check(f"{where}: a writing sample opens in the viewer", s["open"] and s["n"].endswith("of 2") and "/media/sized/1200/" in s["src"])
    page.keyboard.press("Escape")
    wait_closed(page)
    check(f"{where}: Esc closes", not st(page)["open"])


def run(page, pen, ink):
    pen_page(page, pen, "", ".rec-thumbs", "getAttribute('aria-current') === 'true'")
    pen_page(page, pen, "/prev", ".pen-photo-thumbs", "classList.contains('active')")

    for base in ("", "/prev"):
        page.goto(f"{BASE}{base}/inks/{ink}/")
        page.wait_for_load_state("networkidle")
        page.locator("img[data-view-group=swatches]").first.click()
        wait_open(page)
        s = st(page)
        check(f"{base or 'next'}: an ink swatch opens", s["open"] and "swatch" in s["cap"].lower())
        page.go_back()
        wait_closed(page)
        check(f"{base or 'next'}: Back closes it on the ink page", not st(page)["open"] and st(page)["url"] == f"{base}/inks/{ink}/")

    # boosted swap to the pen, then the photo still opens (the kit arms new markup itself)
    page.goto(f"{BASE}/pens/")
    page.wait_for_load_state("networkidle")
    page.evaluate(f"htmx.ajax('GET', '/pens/{pen}/', {{target: '#main', select: '#main', swap: 'outerHTML'}})")
    page.wait_for_selector("#photoImg")
    page.wait_for_timeout(300)
    check("after an htmx swap the photo has role=button", page.get_attribute("#photoImg", "role") == "button")
    page.click("#photoImg")
    wait_open(page)
    check("and it opens", st(page)["open"])
    page.keyboard.press("Escape")
    wait_closed(page)

    # the Gantt's zoom chips (data-zoom) are no pictures any more
    page.goto(f"{BASE}/prev/history/gantt/")
    page.wait_for_load_state("networkidle")
    if page.locator("button.kit-chip[data-zoom='2']").count():
        chip = page.locator("button.kit-chip[data-zoom='2']")
        check("Gantt chip: no role or label from the viewer", chip.get_attribute("role") is None and chip.get_attribute("aria-label") is None)
        chip.click()
        page.wait_for_timeout(300)
        check("Gantt chip 2×: no viewer", not st(page)["open"])
        check(
            "Gantt chip 2×: the chart is twice as wide",
            page.get_attribute("#ganttInner", "data-zoom") == "2" and chip.get_attribute("aria-pressed") == "true",
        )
    else:
        print("skip Gantt: no chart in this copy")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        proc, sess = lp.start(tmp, DB)
        try:
            pen, ink = seed(tmp)
            with sync_playwright() as p:
                b = p.chromium.launch()
                ctx = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, service_workers="block")
                ctx.add_cookies([{"name": "sessionid", "value": sess, "url": BASE}])
                page = ctx.new_page()
                errs = []
                page.on("pageerror", lambda e: errs.append(str(e)))
                run(page, pen, ink)
                check("no page errors", not errs)
                for e in errs:
                    print("   ", e)
                b.close()
        finally:
            proc.terminate()
            proc.wait()
    print(f"\n{len(failures)} failed" if failures else "\nall passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
