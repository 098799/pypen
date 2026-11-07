"""Walk the live site (pen.grining.eu) as the owner, reading only.

A phone (390×844, touch). Every write is refused in the page before any page
script runs (fetch, sendBeacon and XMLHttpRequest send only GET/HEAD), the
service worker is blocked, and no form is submitted. The session is one made
on bae for the walk and deleted after (AUDIT.md, PYPEN-4 and PYPEN-2):

    PYPEN_SESSION=<key> SHOTS=dir PREFIX=after- python3 tools/live_walk.py

Checks each screen: 200, no page error, nothing wider than the phone; the
keyboard palette and ? sheet lock the page and close on Back (PYPEN-8). Then
a desk (1440×900, PYPEN-6): the 52 px bar, its tabs, Filter ▾ (a chip there
filters by a GET), ⌕ and ⋯. DESK=0 skips it; DESK=only walks only it (the
"before" shots of a deploy that adds the bar: the checks then fail, the shots
are what counts).
"""

import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "https://pen.grining.eu")
SESSION = os.environ["PYPEN_SESSION"]
SHOTS = os.environ.get("SHOTS")
PREFIX = os.environ.get("PREFIX", "")
failures = []

READ_ONLY = """
(() => {
  const ok = m => !m || /^(GET|HEAD)$/i.test(m);
  const f = window.fetch;
  window.fetch = function (i, o) {
    const m = (o && o.method) || (i && i.method);
    if (!ok(m)) return Promise.reject(new Error('read-only walk'));
    return f.apply(this, arguments);
  };
  navigator.sendBeacon = () => false;
  const open = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (m) {
    if (!ok(m)) throw new Error('read-only walk');
    return open.apply(this, arguments);
  };
  document.addEventListener('submit', e => { e.preventDefault(); e.stopImmediatePropagation(); }, true);
})();
"""


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def shot(page, name):
    if SHOTS:
        page.screenshot(path=os.path.join(SHOTS, PREFIX + name + ".png"))


def visit(page, path, name=None, status=200):
    errors = []
    on_error = lambda e: errors.append(str(e))  # noqa: E731
    page.on("pageerror", on_error)
    r = page.goto(BASE + path)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(200)
    page.remove_listener("pageerror", on_error)
    check(f"{path}: {status}", r is not None and r.status == status)
    check(f"{path}: no sideways scroll", page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))
    check(f"{path}: no page error {errors}", not errors)
    if name:
        shot(page, name)


def desk(b):
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, service_workers="block")
    ctx.add_init_script(READ_ONLY)
    ctx.add_cookies([{"name": "sessionid", "value": SESSION, "url": BASE}])
    page = ctx.new_page()
    js = page.evaluate
    visit(page, "/prev/dashboard/", "desk-dashboard")
    check("desk: one 52 px bar at the top", js("(() => { const r = document.getElementById('hdr').getBoundingClientRect(); return r.top === 0 && r.height === 52; })()"))
    tabs = js("[...document.querySelectorAll('#hdr nav.kit-tabs a')].filter(a => a.offsetParent).map(a => a.textContent.trim())")
    check(f"desk: six tabs {tabs}", tabs == ["Desk", "Inkings", "Pens", "Inks", "History", "Records"])
    visit(page, "/prev/pens/", "desk-pens")
    page.click("#deskFilterBtn")
    page.wait_for_timeout(400)
    check("desk: Filter opens the rotation chips", js("document.querySelectorAll('#deskFilter.open .db-chips > button').length") > 2)
    shot(page, "desk-pens-filter")
    page.locator("#deskFilter .db-chips > button").nth(1).click()
    page.wait_for_timeout(1500)
    check("desk: a chip filters", "rot=" in page.url)
    check("desk: Filter names it", js("document.querySelector('#deskFilterBtn b').textContent") != "")
    visit(page, "/prev/inks/", "desk-inks")
    page.click("#deskSearchBtn")
    page.wait_for_timeout(400)
    check("desk: ⌕ opens the search", js("document.activeElement.id") == "menuSearchInput")
    shot(page, "desk-search")
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    page.click("#hdr .db-btn[data-menu-btn]")
    page.wait_for_timeout(400)
    check("desk: ⋯ opens the menu", js("document.getElementById('menuPanel').classList.contains('open')"))
    shot(page, "desk-menu")
    page.keyboard.press("Escape")
    ctx.close()


NEXT_SCREENS = [("/dashboard/", "next-desk"), ("/pens/", "next-pens"), ("/pens/?view=grid", None), ("/inks/", "next-inks"),
                ("/inks/?view=list", None), ("/usages/", "next-inkings"), ("/pick/", "next-pick"), ("/search/?q=blue", None),
                ("/settings/", "next-settings"), ("/stats/", "next-stats"), ("/stats/inkings/", "next-stats-inkings"),
                ("/stats/collection/", "next-stats-collection"), ("/stats/cupboard/", "next-stats-cupboard"),
                ("/stats/rotation/", "next-stats-rotation"), ("/stats/timeline/", None), ("/stats/calendar/", "next-stats-calendar"),
                ("/stats/pairs/", None), ("/stats/records/", None), ("/usages/add/", "next-add-inking"),
                ("/pens/add/", None), ("/inks/add/", None), ("/pens/needs-photos/", None), ("/import/", None),
                ("/supen/", "next-supen"), ("/supen/?rot=out&sort=fills", None), ("/suink/", "next-suink")]


def next_walk(b):
    """The new version (PYPEN-11), reading only: tools/next_probe.py does the writes on a copy."""
    ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True, service_workers="block")
    ctx.add_init_script(READ_ONLY)
    ctx.add_cookies([{"name": "sessionid", "value": SESSION, "url": BASE}])
    page = ctx.new_page()
    js = page.evaluate
    failed = []
    page.on("response", lambda r: failed.append(f"{r.status} {r.url}") if r.status >= 400 and "/prev/" not in r.url else None)
    for path, name in NEXT_SCREENS:
        visit(page, path, name)
    check("next: fonts loaded", js("document.fonts.check('600 20px Alegreya') && document.fonts.check('16px \"Alegreya Sans\"')"))
    check("next: nothing failed to load", not failed)
    print(failed[:5])
    visit(page, "/dashboard/")
    check("next: the desk draws swabs", js("document.querySelectorAll('.swab').length") > 0)
    # PYPEN-12: supen and suink are a page; the desk's count of due pens opens it.
    check("next: the desk's due count opens supen", js("document.querySelector('.head-link').getAttribute('href')") == "/supen/")
    page.locator("nav.kit-tabs [data-menu-btn]").tap()
    page.wait_for_timeout(300)
    check("next: More opens", js("document.getElementById('menuPanel').classList.contains('open')"))
    shot(page, "next-menu")
    page.go_back()
    page.wait_for_timeout(300)
    check("next: Back closes it", not js("document.getElementById('menuPanel').classList.contains('open')"))
    page.locator(".fill-photo").first.tap()
    page.wait_for_url("**/next/pens/*/")
    page.wait_for_load_state("networkidle")
    check("next: the pen page is in this version", js("!!document.querySelector('.rec-title')"))
    shot(page, "next-pen")
    page.locator("nav.kit-tabs a", has_text="Inks").tap()
    page.wait_for_url("**/next/inks/")
    page.wait_for_load_state("networkidle")
    page.locator("#inkFilters a[data-color]").first.tap()
    page.wait_for_timeout(1200)
    check("next: a colour chip filters", "color=" in page.url)
    page.locator(".card-ink").first.tap()
    page.wait_for_url("**/next/inks/*/")
    page.wait_for_load_state("networkidle")
    check("next: the ink page has its closest inks", js("document.querySelectorAll('.card-ink').length") > 0)
    shot(page, "next-ink")
    visit(page, "/stats/")
    box = page.locator(".river-plot").bounding_box()
    page.touchscreen.tap(box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.6)
    page.wait_for_timeout(200)
    check("next: the river reads a month", "pens inked" in js("document.querySelector('.river-read').textContent"))
    shot(page, "next-river")
    # Dark.
    js("window.kitTheme && kitTheme.set('dark')")
    page.wait_for_timeout(200)
    shot(page, "next-stats-dark")
    visit(page, "/inks/", "next-inks-dark")
    js("window.kitTheme && kitTheme.set('auto')")
    ctx.close()


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        if os.environ.get("NEXT") == "only":
            next_walk(b)
            b.close()
            print("all passed" if not failures else f"{len(failures)} FAILED: {failures}")
            sys.exit(1 if failures else 0)
        if os.environ.get("DESK") == "only":
            desk(b)
            b.close()
            print("all passed" if not failures else f"{len(failures)} FAILED: {failures}")
            sys.exit(1 if failures else 0)
        ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True, service_workers="block")
        ctx.add_init_script(READ_ONLY)
        ctx.add_cookies([{"name": "sessionid", "value": SESSION, "url": BASE}])
        page = ctx.new_page()
        visit(page, "/prev/dashboard/", "desk")
        visit(page, "/prev/usages/", "inkings")
        page.locator("#usageQ").type("pilot blue", delay=40)
        try:
            page.wait_for_url("**q=pilot*", timeout=8000)
        except Exception:
            pass
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(300)
        check("inkings: the search is in the URL", "q=pilot" in page.url)
        check("inkings: the words are marked", page.evaluate("document.querySelectorAll('#main mark').length") > 0)
        page.evaluate("document.activeElement && document.activeElement.blur()")
        shot(page, "inkings-search")
        visit(page, "/prev/inks/?q=diamine", "inks-search")
        visit(page, "/api/pens?limit=1000", status=422)
        visit(page, "/prev/pens/", "pens")
        # PYPEN-7: 50 rows a page, Load more appends, no heading twice.
        n_rows = "document.querySelectorAll('#main [data-listnav-item]').length"
        n_heads = "[...document.querySelectorAll('#main [data-more-head] h3')].map(h => h.textContent)"
        check("pens: 50 on the first page", page.evaluate(n_rows) == 50)
        page.locator("a[data-more]").click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(400)
        hs = page.evaluate(n_heads)
        check("pens: Load more appends 50", page.evaluate(n_rows) == 100)
        check(f"pens: no heading twice {hs}", len(hs) == len(set(hs)))
        page.evaluate("document.querySelector('.more-nav').scrollIntoView({block: 'center'})")
        shot(page, "pens-load-more")
        pen = page.locator("#main a[href^='/prev/pens/']").evaluate_all(
            "as => as.map(a => a.getAttribute('href')).find(h => /^\\/prev\\/pens\\/\\d+\\/$/.test(h))"
        )
        visit(page, pen, "pen")
        if page.locator("#photoMain img[data-zoom]").count():
            page.locator("#photoMain img[data-zoom]").click()
            page.wait_for_timeout(1500)
            check("viewer: opens", page.evaluate("!!document.querySelector('dialog.pv[open]')"))
            check("viewer: page locked", page.evaluate("document.documentElement.classList.contains('scroll-lock')"))
            shot(page, "viewer")
            page.go_back()
            page.wait_for_timeout(700)
            check("viewer: Back closes it, stays", not page.evaluate("!!document.querySelector('dialog.pv[open]')") and page.url.endswith(pen))
            check("viewer: lock gone", not page.evaluate("document.documentElement.classList.contains('scroll-lock')"))
        visit(page, "/prev/inks/", "inks")
        ink = page.locator("#main a[href^='/prev/inks/']").evaluate_all(
            "as => as.map(a => a.getAttribute('href')).find(h => /^\\/prev\\/inks\\/\\d+\\/$/.test(h))"
        )
        visit(page, ink, "ink")
        for u in (
            "/prev/history/",
            "/prev/history/inkings/",
            "/prev/history/inkings/?y=2024",
            "/prev/usages/?began=2024-08",
            "/prev/history/calendar/",
            "/prev/history/gantt/",
            "/prev/history/matrix/",
            "/prev/records/",
            "/prev/pick/",
            "/prev/search/?q=lamy",
            "/prev/import/",
            "/prev/pens/needs-photos/",
            "/prev/usages/add/",
        ):
            visit(page, u)
        visit(page, "/prev/settings/", "settings")
        if page.locator("button[data-whatsnew-open]").count():
            page.locator("button[data-whatsnew-open]").click()
            page.wait_for_timeout(900)
            check("whatsnew: opens", page.evaluate("!!document.querySelector('dialog#kit-wn[open]')"))
            shot(page, "whatsnew")
            page.go_back()
            page.wait_for_timeout(700)
            check("whatsnew: Back closes it", not page.evaluate("!!document.querySelector('dialog#kit-wn[open]')"))
        visit(page, "/prev/pens/")
        page.locator("nav.kit-tabs [data-menu-btn]").click()
        page.wait_for_timeout(500)
        check("menu: opens", page.evaluate("document.getElementById('menuPanel').classList.contains('open')"))
        shot(page, "menu")
        page.go_back()
        page.wait_for_timeout(500)
        # The keyboard palette and the ? sheet (PYPEN-8, KEYS-LAYER v1.3): kit
        # layers, so the page under them is locked and Back closes them.
        visit(page, "/prev/pens/")
        on = "document.getElementById('%s').classList.contains('on')"
        locked = "document.documentElement.classList.contains('scroll-lock')"
        page.keyboard.press("Control+k")
        page.wait_for_timeout(500)
        check("palette: opens", page.evaluate(on % "kpal"))
        check("palette: page locked", page.evaluate(locked))
        shot(page, "palette")
        page.go_back()
        page.wait_for_timeout(700)
        check("palette: Back closes it, stays", not page.evaluate(on % "kpal") and page.url.endswith("/prev/pens/"))
        if page.url.endswith("/prev/pens/"):
            page.keyboard.press("?")
            page.wait_for_timeout(500)
            check("? sheet: opens", page.evaluate(on % "khelp"))
            check("? sheet: page locked", page.evaluate(locked))
            check("? sheet: names no path of the box", "~/apps" not in page.evaluate("document.getElementById('khelp').textContent"))
            shot(page, "keys-sheet")
            page.go_back()
            page.wait_for_timeout(700)
            check("? sheet: Back closes it, stays", not page.evaluate(on % "khelp") and page.url.endswith("/prev/pens/"))
        visit(page, "/pub/pens/wall/", "pen-wall")
        visit(page, "/pub/inks/wall/")
        visit(page, "/prev/pens/no-such-page/", "404", status=404)
        if os.environ.get("DESK") != "0":
            desk(b)
        b.close()
    print("all passed" if not failures else f"{len(failures)} FAILED: {failures}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
