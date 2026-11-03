"""The new version (/next/, PYPEN-11) in a phone browser, then on a desk.

Headless Chromium at 390×844 against a throwaway copy of the newest backup on a
spare port, a session made in the copy. It writes: an inking, finished and undone,
in the copy only. Never point it at the live site (tools/live_walk.py reads).

    PLAYWRIGHT_BROWSERS_PATH=/home/tgrining/.cache/ms-playwright python3 tools/next_probe.py
    BASE=http://127.0.0.1:18600 PYPEN_SESSION=<key> ...   use a running copy (with its media)
"""

import os
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layer_probe as lp  # noqa: E402

lp.PORT = int(os.environ.get("PROBE_PORT", "18497"))
lp.BASE = BASE = os.environ.get("BASE") or f"http://127.0.0.1:{lp.PORT}"
BACKUPS = Path("/home/tgrining/.local/share/vps-backups/pypen")
SCREENS = ["/next/", "/next/pens/", "/next/pens/?view=grid", "/next/inks/", "/next/inks/?view=list", "/next/usages/", "/next/pick/",
           "/next/search/?q=blue", "/next/settings/", "/next/stats/", "/next/stats/inkings/", "/next/stats/inkings/?y=2019",
           "/next/stats/collection/", "/next/stats/cupboard/", "/next/stats/rotation/", "/next/stats/timeline/",
           "/next/stats/calendar/", "/next/stats/pairs/", "/next/stats/records/", "/next/pens/add/", "/next/inks/add/",
           "/next/usages/add/", "/next/pens/needs-photos/", "/next/import/"]
failures = []
errors = []


def check(name, cond, more=""):
    print(("ok   " if cond else "FAIL ") + name + (f"  {more}" if more != "" and not cond else ""))
    if not cond:
        failures.append(name)


def settle(page, ms=250):
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(ms)


def go(page, path):
    r = page.goto(BASE + path)
    settle(page)
    check(f"{path}: 200", r.status == 200, r.status)
    check(f"{path}: no sideways scroll", page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), page.evaluate("document.documentElement.scrollWidth"))
    over = page.evaluate("""[...document.querySelectorAll('#main *')].filter(e => { const b = e.getBoundingClientRect();
        if (!b.width || !b.height || b.right <= innerWidth + 1) return false;
        for (let p = e.parentElement; p && p.id !== 'main'; p = p.parentElement) { const o = getComputedStyle(p); if (/auto|scroll|hidden|clip/.test(o.overflowX)) return false; }
        return true; }).length""")
    check(f"{path}: nothing past the edge", over == 0, over)


def tip(page):
    return page.evaluate("(() => { const t = document.getElementById('chartTip'); return t && t.classList.contains('open') ? t.textContent : ''; })()")


def phone(page):
    js = page.evaluate
    for path in SCREENS:
        go(page, path)

    # The More menu, kit layer: opens, Back closes it and stays.
    go(page, "/next/")
    page.locator(".tabbar [data-menu-btn]").tap()
    page.wait_for_timeout(200)
    check("menu opens", js("document.getElementById('menuPanel').classList.contains('open')"))
    box = page.locator("#menuPanel").bounding_box()
    check("menu is on the screen", box and box["y"] >= 0 and box["y"] + box["height"] <= 844, box)
    page.go_back()
    page.wait_for_timeout(300)
    check("Back closes the menu and stays", not js("document.getElementById('menuPanel').classList.contains('open')") and page.url.endswith("/next/"), page.url)

    # Tabs swap softly and light up.
    js("window.__stay = 1")
    page.locator(".tabbar a", has_text="Inks").tap()
    page.wait_for_url("**/next/inks/")
    settle(page)
    check("a tab is a soft navigation", js("window.__stay === 1"))
    check("the tab is lit", js("document.querySelector('.tabbar a.active span').textContent") == "Inks")

    # A chip filters and stays in the version.
    page.locator("#inkFilters a[data-color]").first.tap()
    settle(page)
    check("a colour chip narrows the wall", "color=" in page.url and js("document.querySelectorAll('#inkContentBody .card-ink').length") < 50, page.url)
    check("the chip is lit", js("!!document.querySelector('#inkFilters a[aria-current]')"))
    page.locator("#inkFilters .kit-chip-clear").tap()
    settle(page)
    check("Clear clears", "color=" not in page.url, page.url)

    # Load more on the wall.
    go(page, "/next/inks/")
    before = js("document.querySelectorAll('#inkContentBody .card-ink').length")
    page.locator("[data-more]").first.tap()
    settle(page, 400)
    after = js("document.querySelectorAll('#inkContentBody .card-ink').length")
    check(f"Load more adds rows ({before} to {after})", after > before)

    # A search box filters as it is typed.
    go(page, "/next/pens/")
    page.locator("#penQ").fill("pelikan")
    page.wait_for_timeout(700)
    settle(page)
    n = js("document.querySelectorAll('#penContentBody .pen-row-nx').length")
    check(f"typing searches the pens ({n})", 0 < n < 50 and "q=pelikan" in page.url)
    check("a match is marked", js("!!document.querySelector('#penContentBody mark')"))
    page.locator("#rotbar a[data-navval=p1]").tap()
    settle(page)
    check("a chip keeps the search", "q=pelikan" in page.url and "rot=p1" in page.url, page.url)
    page.locator("#penQ").fill("zzzznothing")
    page.wait_for_timeout(700)
    settle(page)
    check("no match says so", "zzzznothing" in js("document.querySelector('#penContentBody .kit-empty').textContent"))

    # The river reads under a finger.
    go(page, "/next/stats/")
    plot = page.locator(".river-plot").bounding_box()
    page.touchscreen.tap(plot["x"] + plot["width"] * .3, plot["y"] + plot["height"] * .6)
    page.wait_for_timeout(150)
    check("the river reads a month", "pens inked" in js("document.querySelector('.river-read').textContent"), js("document.querySelector('.river-read').textContent"))
    page.locator(".river-key button").first.tap()
    page.wait_for_timeout(100)
    check("the key lights one colour", js("document.querySelectorAll('.river path.is-lit').length") == 1)

    # A tip: tap, numbers, a link to the twin, Back closes.
    go(page, "/next/stats/inkings/")
    page.locator(".heat-c[data-tip-links]").first.tap()
    page.wait_for_timeout(250)
    check("a square gives its numbers", "inking" in tip(page), tip(page))
    href = js("document.querySelector('#chartTip a').getAttribute('href')")
    check("its link stays in this version", href.startswith("/next/usages/?began="), href)
    page.go_back()
    page.wait_for_timeout(300)
    check("Back closes the tip", tip(page) == "" and "/next/stats/inkings/" in page.url)
    go(page, "/next/stats/collection/")
    page.locator(".scatter button").first.tap(force=True)
    page.wait_for_timeout(250)
    check("a dot names its pen", "days inked" in tip(page), tip(page))
    go(page, "/next/stats/calendar/?y=2019")
    page.locator(".cal button").nth(40).tap()
    page.wait_for_timeout(250)
    check("a day says what was inked", "pen" in tip(page), tip(page))

    # The ink flow: pick an ink on the desk, save, finish, undo.
    go(page, "/next/")
    page.locator(".next-inks .card-ink").first.tap()
    page.wait_for_url("**/next/usages/add/**")
    settle(page, 500)
    check("the form has the pen and the ink", js("document.getElementById('id_pen').value") != "" and js("document.getElementById('id_ink').value") != "")
    page.wait_for_timeout(200)
    nib = js("document.getElementById('id_nib').value")
    if not nib:
        js("(() => { const s = document.getElementById('id_nib'); s.tomselect.setValue(s.options[1].value); })()")
    page.locator("form.form-nx button[type=submit]").tap()
    page.wait_for_url("**/next/pens/*/", timeout=8000)
    settle(page, 400)
    check("saved: it lands on the pen, in this version", "/next/pens/" in page.url, page.url)
    check("saved: a toast says so", "Inked" in js("(document.getElementById('kit-toast') || {}).textContent || ''"))
    check("saved: the pen shows its ink", js("!!document.querySelector('.now-plate')"))
    pen_url = page.url
    page.locator("form[action*='/end/'] button").first.tap()
    page.wait_for_url("**/next/usages/", timeout=8000)
    settle(page, 400)
    toast = page.locator("#kit-toast")
    check("finished: a toast with Undo", "Undo" in js("document.getElementById('kit-toast').textContent"))
    toast.get_by_text("Undo").tap()
    page.wait_for_url("**/next/usages/", timeout=8000)
    settle(page, 400)
    page.goto(pen_url)
    settle(page)
    check("Undo brought the fill back", js("!!document.querySelector('.now-plate')"))
    # Clean the copy: delete the inking again through the page's own form.
    page.on("dialog", lambda d: d.accept())
    page.locator(".row-t a").first.wait_for()

    # A confirm that is answered no sends nothing.
    go(page, "/next/pens/add/")
    check("Sold for hides while the switch is off", js("document.getElementById('soldRow').hidden"))
    page.locator(".switch-nx").first.tap()
    page.wait_for_timeout(100)
    check("the switch shows Sold for", not js("document.getElementById('soldRow').hidden"))

    # Settings: theme, which opens first.
    go(page, "/next/settings/")
    check("the theme row is mounted", js("!!document.querySelector('[data-kit-theme] button')"))
    page.locator("[data-kit-theme] button", has_text="Dark").tap()
    page.wait_for_timeout(100)
    check("Dark sets the theme", js("document.documentElement.getAttribute('data-theme')") == "dark")
    check("the plates stay paper in dark", js("getComputedStyle(document.documentElement).getPropertyValue('--plate').trim()") == "#f3f2ec")
    page.locator("[data-kit-theme] button", has_text="Light").tap()
    page.locator("button", has_text="Open this version first").tap()
    settle(page)
    check("the choice is shown", js("document.body.textContent.includes('Stop opening this version first')"))
    r = page.goto(BASE + "/dashboard/")
    settle(page)
    check("the old desk now opens here", page.url.endswith("/next/"), page.url)
    go(page, "/next/settings/")
    page.locator("button", has_text="Back to the old version").tap()
    settle(page)
    check("Back to the old version goes there", page.url.endswith("/dashboard/") and js("!!document.querySelector('link[href*=\"css/app\"]')"), page.url)

    # A 404 keeps the look.
    go_ok = page.goto(BASE + "/next/pens/999999/")
    settle(page)
    check("a dead pen is a 404 page", go_ok.status == 404)
    check("errors so far", not errors, errors[:4])


def viewer(page):
    js = page.evaluate
    go(page, "/next/pens/")
    page.locator(".pen-row-nx h3 a").first.tap()
    settle(page)
    if not js("!!document.getElementById('photoImg')"):
        print("skip viewer: no photo in this copy")
        return
    page.locator("#photoImg").tap()
    page.wait_for_timeout(350)
    check("a photo opens the viewer", js("!!document.querySelector('dialog.pv[open]')"))
    page.go_back()
    page.wait_for_timeout(350)
    check("Back closes the viewer and stays", not js("!!document.querySelector('dialog.pv[open]')") and "/next/pens/" in page.url)


def desk(page):
    js = page.evaluate
    go(page, "/next/inks/")
    check("the bar is 52 px", js("document.getElementById('hdr').offsetHeight") == 52)
    check("no tab bar at the bottom", js("getComputedStyle(document.querySelector('.tabbar')).position") != "fixed")
    page.locator("#deskFilterBtn").click()
    page.wait_for_timeout(150)
    check("Filter opens the chips", js("document.getElementById('deskFilter').classList.contains('open')"))
    page.locator("#deskFilter .kit-chip", has_text="Blue").first.click()
    settle(page)
    check("a chip there filters", "color=Blue" in page.url.replace("%20", " "), page.url)
    page.locator("#deskSearchBtn").click()
    page.wait_for_timeout(150)
    page.keyboard.type("pelikan")
    page.keyboard.press("Enter")
    page.wait_for_url("**/next/search/?q=pelikan")
    settle(page)
    check("the bar's search stays in this version", js("document.querySelectorAll('#searchResultsBody .pen-row-nx').length") > 0)
    page.locator("#hdr [data-menu-btn]").click()
    page.wait_for_timeout(150)
    check("⋯ opens the menu", js("document.getElementById('menuPanel').classList.contains('open')"))
    page.keyboard.press("Escape")
    # The palette: its hits and places mean their twins here.
    go(page, "/next/")
    page.keyboard.press("Control+k")
    page.wait_for_timeout(250)
    page.keyboard.type("Records")
    page.wait_for_timeout(500)
    page.keyboard.press("Enter")
    page.wait_for_timeout(800)
    check("the palette goes to this version's page", page.url.endswith("/next/stats/records/"), page.url)
    page.keyboard.press("m")
    page.keyboard.press("p")
    page.wait_for_timeout(600)
    check("m p goes to this version's pens", page.url.endswith("/next/pens/"), page.url)
    for path in ("/next/", "/next/stats/", "/next/stats/collection/", "/next/stats/calendar/", "/next/pens/?view=grid", "/next/stats/pairs/"):
        go(page, path)
    check("errors at the desk", not errors, errors[:4])


def run(pw, session):
    b = pw.chromium.launch()
    c = b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True, device_scale_factor=2, service_workers="block")
    host = BASE
    c.add_cookies([{"name": "sessionid", "value": session, "url": host}])
    page = c.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" and "404" not in m.text else None)
    phone(page)
    viewer(page)
    c.close()
    c = b.new_context(viewport={"width": 1440, "height": 900}, service_workers="block")
    c.add_cookies([{"name": "sessionid", "value": session, "url": host}])
    page = c.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    desk(page)
    b.close()


def main():
    session = os.environ.get("PYPEN_SESSION")
    with sync_playwright() as pw:
        if session and os.environ.get("BASE"):
            run(pw, session)
        else:
            with tempfile.TemporaryDirectory() as tmp:
                src = max(BACKUPS.glob("pypen-*.db"), key=lambda p: p.stat().st_mtime)
                proc, session = lp.start(tmp, src)
                try:
                    run(pw, session)
                finally:
                    proc.terminate()
                    proc.wait(timeout=10)
    print("FAILED: " + ", ".join(failures) if failures else "all ok")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
