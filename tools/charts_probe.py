"""The inking charts in a phone browser (PYPEN-10), then a desk.

Headless Chromium at 390×844 against a throwaway copy of a database (the newest
backup, or PROBE_DB) on a spare port, a session made in the copy, every non-GET
refused: never the live data.

    PLAYWRIGHT_BROWSERS_PATH=/home/tgrining/.cache/ms-playwright python3 tools/charts_probe.py
    SHOTS=dir  ... also saves the screens, dark and light.

Checks: no sideways scroll; a tap on a bar and on a month square gives numbers, and
Back closes them and stays; See them opens the list narrowed, and × leaves it; a
year chip draws a year; the line reads under a finger; the key lights one family;
the calendar and the matrix answer a tap; a record page has its bars.
"""

import os
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layer_probe as lp  # noqa: E402

lp.PORT = int(os.environ.get("PROBE_PORT", "18498"))
lp.BASE = BASE = f"http://127.0.0.1:{lp.PORT}"
BACKUPS = Path("/home/tgrining/.local/share/vps-backups/pypen")
SHOTS = os.environ.get("SHOTS")
failures = []


def check(name, cond, more=""):
    print(("ok   " if cond else "FAIL ") + name + (f"  {more}" if more != "" and not cond else ""))
    if not cond:
        failures.append(name)


def shot(page, name, **kw):
    if SHOTS:
        page.screenshot(path=str(Path(SHOTS) / f"{name}.png"), **kw)


def go(page, path):
    errors = []
    h = lambda e: errors.append(str(e))  # noqa: E731
    page.on("pageerror", h)
    r = page.goto(BASE + path)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(200)
    page.remove_listener("pageerror", h)
    check(f"{path}: 200", r.status == 200, r.status)
    check(f"{path}: no sideways scroll", page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), page.evaluate("document.documentElement.scrollWidth"))
    check(f"{path}: no page error", not errors, errors)


TIP = "(() => { const t = document.getElementById('chartTip'); return t && t.classList.contains('open') ? t.textContent : ''; })()"


def run(page):
    js = page.evaluate
    go(page, "/prev/history/inkings/")
    check("tab lit", js("document.querySelector('.history-sub-nav a.active').textContent") == "Inkings")
    check("All lit", js("document.querySelector('nav[aria-label=Year] [aria-current]').textContent") == "All")
    n = js("document.querySelectorAll('.bars:not(.is-plain) .bar-col').length")
    check(f"a column a year ({n})", n >= 2)
    over = js("""[...document.querySelectorAll('.chart-box, .rank-row, .heat, .bars')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).length""")
    check("nothing past the edge", over == 0, over)
    shot(page, "charts-phone-top")
    # A bar: tap, numbers, Back closes and stays.
    page.locator(".bars:not(.is-plain) .bar-col").nth(1).tap()
    page.wait_for_timeout(300)
    tip = js(TIP)
    check("bar: a tap gives its numbers", "inking" in tip, tip)
    shot(page, "charts-phone-tip")
    page.go_back()
    page.wait_for_timeout(500)
    check("bar: Back closes it and stays", js(TIP) == "" and page.url.endswith("/prev/history/inkings/"), page.url)
    # A square: tap outside closes.
    page.locator(".heat-c:not(.is-ahead)[data-tip-links]").first.tap()
    page.wait_for_timeout(300)
    check("square: a tap gives its numbers", "inking" in js(TIP))
    page.locator(".page-head h1").tap()
    page.wait_for_timeout(300)
    check("square: a tap elsewhere closes it", js(TIP) == "")
    # See them
    page.locator(".heat-c:not(.is-ahead)[data-tip-links]").first.tap()
    page.wait_for_timeout(300)
    page.locator("#chartTip a").first.click()
    page.wait_for_url("**/usages/?began=*", timeout=8000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(300)
    check("See them: the list narrowed", "began=" in page.url and js("!!document.querySelector('nav[aria-label=\"Part of the inkings\"] .kit-chip')"))
    check("See them: the tip is gone", js(TIP) == "")
    shot(page, "charts-phone-list")
    total = js("document.querySelector('[data-more-head] .aside').textContent")
    page.locator("#usageQ").type("zzzznope", delay=20)
    page.wait_for_url("**q=zzzznope*", timeout=8000)
    check("search keeps the month", "began=" in page.url, page.url)
    page.locator("#usageQ").fill("")
    page.wait_for_timeout(800)
    page.locator("nav[aria-label=\"Part of the inkings\"] .kit-chip").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(300)
    check("× leaves the month", "began=" not in page.url, page.url)
    check("× shows more", js("document.querySelector('[data-more-head] .aside').textContent") != total)
    # A year chip.
    go(page, "/prev/history/inkings/")
    page.locator("nav[aria-label=Year] .kit-chip", has_text="2024").click()
    page.wait_for_url("**y=2024", timeout=8000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(300)
    check("a year: 12 columns", js("document.querySelectorAll('.bars:not(.is-plain) .bar-col').length") == 12)
    check("a year: the chip is lit", js("document.querySelector('nav[aria-label=Year] [aria-current]').textContent") == "2024")
    check("a year: no month grid", js("!document.querySelector('.heat')"))
    shot(page, "charts-phone-year")
    # The line under a finger.
    page.locator("[data-line]").scroll_into_view_if_needed()
    box = page.locator(".line-plot").bounding_box()
    page.touchscreen.tap(box["x"] + box["width"] * 0.5, box["y"] + 30)
    page.wait_for_timeout(200)
    read = js("document.querySelector('[data-line-read]').textContent")
    check("line: reads under a tap", "2024:" in read and "pen" in read, read)
    # The key.
    page.locator(".fam-key").first.tap()
    page.wait_for_timeout(100)
    check("key: lights one family", js("document.querySelectorAll('.is-picked .bar-stack i:not(.is-lit)').length") > 0)
    page.locator(".fam-key").first.tap()
    check("key: a second tap, all", js("document.querySelectorAll('.is-picked').length") == 0)
    # The whole page, for the eye.
    go(page, "/prev/history/inkings/")
    shot(page, "charts-phone-full", full_page=True)
    # Older tabs: taps now answer on a phone.
    go(page, "/prev/history/calendar/")
    page.locator(".cal-cell.is-inked").nth(20).scroll_into_view_if_needed()
    page.locator(".cal-cell.is-inked").nth(20).tap()
    page.wait_for_timeout(300)
    check("calendar: a tap names the day's inks", js(TIP) != "")
    shot(page, "calendar-tip")
    page.go_back()
    page.wait_for_timeout(400)
    go(page, "/prev/history/matrix/")
    page.locator(".pi-cell:not(.is-blank)").first.scroll_into_view_if_needed()
    page.locator(".pi-cell:not(.is-blank)").first.tap()
    page.wait_for_timeout(300)
    check("matrix: a tap reads the cell, stays", "day" in js(TIP) and "/prev/history/matrix/" in page.url, js(TIP))
    shot(page, "matrix-tip")
    page.go_back()
    page.wait_for_timeout(400)
    for u in ("/prev/history/", "/prev/history/gantt/"):
        go(page, u)
    # Record pages. Find a pen with years to compare in the top list.
    go(page, "/prev/history/inkings/")
    pen = js("document.querySelector('a.rank-row[href^=\"/prev/pens/\"]').getAttribute('href')")
    ink = js("document.querySelector('a.rank-row[href^=\"/prev/inks/\"]').getAttribute('href')")
    for u, name in ((pen, "pen"), (ink, "ink")):
        go(page, u)
        check(f"{name} page: its bars", js("document.querySelectorAll('.bars.is-small .bar-col').length") >= 2)
        page.locator(".bars.is-small").scroll_into_view_if_needed()
        page.wait_for_timeout(150)
        shot(page, f"record-{name}-bars")


def desk(page):
    go(page, "/prev/history/inkings/")
    check("desk: two columns of charts", page.evaluate("getComputedStyle(document.querySelector('.ink-charts')).gridTemplateColumns.split(' ').length") == 2)
    shot(page, "charts-desk", full_page=True)
    page.locator(".bars:not(.is-plain) .bar-col").nth(2).hover()
    page.wait_for_timeout(200)
    check("desk: hover shows the tip", page.evaluate(TIP) != "")
    page.locator(".page-head h1").hover()
    page.wait_for_timeout(200)
    check("desk: it goes when the pointer leaves", page.evaluate(TIP) == "")
    page.locator(".line-plot").scroll_into_view_if_needed()
    box = page.locator(".line-plot").bounding_box()
    page.mouse.move(box["x"] + box["width"] * 0.3, box["y"] + 20)
    page.wait_for_timeout(100)
    check("desk: line reads under the pointer", "pen" in page.evaluate("document.querySelector('[data-line-read]').textContent"))


def main():
    src = Path(os.environ["PROBE_DB"]) if os.environ.get("PROBE_DB") else max(BACKUPS.glob("pypen-*.db"), key=lambda p: p.stat().st_mtime)
    with tempfile.TemporaryDirectory() as tmp:
        if (BACKUPS / "pen-media").is_dir():
            os.symlink(BACKUPS / "pen-media", Path(tmp) / "media")
        proc, sess = lp.start(tmp, src=src)
        try:
            with sync_playwright() as p:
                b = p.chromium.launch()

                def ctx(**kw):
                    c = b.new_context(service_workers="block", **kw)
                    c.add_cookies([{"name": "sessionid", "value": sess, "url": BASE}])
                    c.route("**/*", lambda r: r.abort() if r.request.method not in ("GET", "HEAD") else r.continue_())
                    return c
                phone = dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
                run(ctx(color_scheme="light", **phone).new_page())
                page = ctx(color_scheme="dark", **phone).new_page()
                go(page, "/prev/history/inkings/")
                shot(page, "charts-phone-dark", full_page=True)
                desk(ctx(viewport={"width": 1440, "height": 900}, color_scheme="light").new_page())
                b.close()
        finally:
            proc.terminate()
            proc.wait()
    print("all passed" if not failures else f"{len(failures)} FAILED: {failures}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
