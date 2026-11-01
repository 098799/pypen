"""The photo viewer (PYPEN-1, static/items/js/viewer.js) in a real browser.

Headless Chromium at 390×844 (touch) against a throwaway copy of the local
database, with made-up photos in a temp media folder: never the live data on
bae, never the local db.sqlite3 itself. Shares layer_probe's start-up.

    python3 tools/viewer_probe.py            # playwright on the system python
    SHOTS=/some/dir python3 tools/viewer_probe.py   # also keep screenshots
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
    return page.evaluate("""() => { const d = document.getElementById('pv');
      return { open: !!(d && d.open), lock: document.documentElement.classList.contains('scroll-lock'),
               n: d ? d.querySelector('.pv-n').textContent : '', t: d ? d.querySelector('.pv-t').textContent : '',
               zoomed: !!(d && d.classList.contains('zoomed')), src: d ? (d.querySelector('.pv-img').getAttribute('src') || '') : '',
               w: d ? d.querySelector('.pv-img').getBoundingClientRect().width : 0,
               next: d ? !d.querySelector('.pv-next').hidden : false, url: location.pathname } }""")


def shot(page, name):
    if SHOTS:
        page.screenshot(path=str(Path(SHOTS) / name))


def pointer(page, kind, pid, x, y):
    page.evaluate(
        """([k, id, x, y]) => document.getElementById('pv').dispatchEvent(
        new PointerEvent(k, {pointerId: id, clientX: x, clientY: y, bubbles: true, pointerType: 'touch', isPrimary: id === 1}))""",
        [kind, pid, x, y],
    )


def run(page, pen, ink):
    page.goto(f"{BASE}/pens/{pen}/")
    page.wait_for_load_state("networkidle")
    shot(page, "pen-page.png")
    check("the page is no wider than the phone",
          page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
    check("the photo sits inside the screen",
          page.evaluate("document.getElementById('photoMain').getBoundingClientRect().right <= innerWidth"))
    # PYPEN-3: the page draws a ~900 px WebP copy; the viewer below still
    # waits for the stored 2400 px file.
    drawn = page.evaluate("(() => { const i = document.getElementById('photoImg'); return [i.currentSrc, i.naturalWidth]; })()")
    check(f"the page draws the 900 px copy {drawn}", "/media/sized/900/" in drawn[0] and drawn[0].endswith(".webp") and drawn[1] == 900)
    tiles = page.evaluate("[...document.querySelectorAll('.samples-strip img')].map(i => i.getAttribute('src'))")
    check(f"the samples draw 600 px copies {tiles}", tiles and all("/media/sized/600/" in t for t in tiles))
    hist = page.evaluate("history.length")
    page.click("#photoImg")
    page.wait_for_function("document.getElementById('pv') && document.getElementById('pv').open")
    page.wait_for_function("document.querySelector('#pv .pv-img').naturalWidth >= 1800")
    s = st(page)
    check("tap the photo: the viewer opens", s["open"])
    check("the page under it is locked", s["lock"])
    check("caption says the pen and 1 of 6", s["n"] == "1 of 6" and "uncapped" in s["t"])
    check("it shows the full file, fitted to the width", 380 <= s["w"] <= 391)
    shot(page, "viewer-open.png")

    page.click("#pv .pv-next")
    page.wait_for_timeout(400)
    s = st(page)
    check("› walks to the next photo", s["n"] == "2 of 6" and "nib" in s["t"] and s["src"])

    # a sideways swipe walks on, too
    pointer(page, "pointerdown", 1, 300, 420)
    pointer(page, "pointermove", 1, 150, 425)
    pointer(page, "pointerup", 1, 150, 425)
    page.wait_for_timeout(300)
    check("a swipe left walks on", st(page)["n"] == "3 of 6")
    for _ in range(3):
        page.click("#pv .pv-next")
    page.wait_for_timeout(300)
    check("at the end, no ›", st(page)["n"] == "6 of 6" and not st(page)["next"])

    # pinch: two fingers apart
    pointer(page, "pointerdown", 1, 170, 420)
    pointer(page, "pointerdown", 2, 220, 420)
    for k in range(1, 6):
        pointer(page, "pointermove", 1, 170 - 20 * k, 420)
        pointer(page, "pointermove", 2, 220 + 20 * k, 420)
    pointer(page, "pointerup", 1, 70, 420)
    pointer(page, "pointerup", 2, 320, 420)
    s = st(page)
    check("pinch zooms in", s["zoomed"] and s["w"] > 900)
    shot(page, "viewer-zoomed.png")

    # double tap at rest zooms, again fits
    page.wait_for_timeout(400)
    pointer(page, "pointerdown", 1, 195, 420)
    pointer(page, "pointerup", 1, 195, 420)
    pointer(page, "pointerdown", 1, 195, 420)
    pointer(page, "pointerup", 1, 195, 420)
    check("double tap while zoomed fits again", not st(page)["zoomed"])
    page.wait_for_timeout(400)
    pointer(page, "pointerdown", 1, 195, 420)
    pointer(page, "pointerup", 1, 195, 420)
    pointer(page, "pointerdown", 1, 195, 420)
    pointer(page, "pointerup", 1, 195, 420)
    check("double tap zooms in", st(page)["zoomed"])

    page.go_back()
    page.wait_for_timeout(400)
    s = st(page)
    check("Back closes the viewer and stays on the pen", not s["open"] and s["url"] == f"/pens/{pen}/")
    check("the lock is gone", not s["lock"])
    check("history is where it was", page.evaluate("history.length") >= hist)

    # a thumb chooses, then the main photo opens at it
    page.click(".pen-photo-thumbs a:nth-child(3)")
    page.click("#photoImg")
    page.wait_for_timeout(300)
    check("the photo opens at the thumb chosen", st(page)["n"] == "3 of 6")
    page.click("#pv .pv-close")
    page.wait_for_timeout(400)
    check("✕ closes", not st(page)["open"] and page.url.endswith(f"/pens/{pen}/"))

    # flick down closes
    page.click("#photoImg")
    page.wait_for_timeout(300)
    pointer(page, "pointerdown", 1, 195, 300)
    pointer(page, "pointermove", 1, 198, 500)
    pointer(page, "pointerup", 1, 198, 500)
    page.wait_for_timeout(400)
    check("a flick down closes", not st(page)["open"])

    # samples on the pen page
    page.locator(".samples-strip img").first.scroll_into_view_if_needed()
    page.locator(".samples-strip img").first.click()
    page.wait_for_timeout(400)
    s = st(page)
    check("a writing sample opens in the viewer", s["open"] and s["n"].endswith("of 2") and s["url"] == f"/pens/{pen}/")
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)
    check("Esc closes", not st(page)["open"])

    # soft navigation (hx-boost) to the ink page, then its swatch
    page.goto(f"{BASE}/inks/{ink}/")
    page.wait_for_load_state("networkidle")
    page.locator("[data-zoom-item=swatches]").first.click()
    page.wait_for_timeout(400)
    s = st(page)
    check("an ink swatch opens", s["open"] and "swatch" in s["t"])
    page.go_back()
    page.wait_for_timeout(300)
    check("Back closes it on the ink page", not st(page)["open"] and st(page)["url"] == f"/inks/{ink}/")

    # boosted swap from the ink page to the pen, then the photo still opens
    page.goto(f"{BASE}/pens/")
    page.wait_for_load_state("networkidle")
    page.evaluate(f"htmx.ajax('GET', '/pens/{pen}/', {{target: '#main', select: '#main', swap: 'outerHTML'}})")
    page.wait_for_selector("#photoImg")
    page.wait_for_timeout(300)
    page.click("#photoImg")
    page.wait_for_timeout(300)
    check("after an htmx swap the photo still opens", st(page)["open"])
    check("and it has role=button", page.get_attribute("#photoImg", "role") == "button")
    page.keyboard.press("Escape")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        proc, sess = lp.start(tmp)
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
