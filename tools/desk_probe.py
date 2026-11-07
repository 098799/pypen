"""The desk bar and the header row (PYPEN-6) in a real browser.

Headless Chromium against a throwaway copy of the local database on a spare
port (layer_probe's start-up): never the live data on bae, never the local
db.sqlite3 itself. At 1440×900: one 52 px bar with the brand, the tabs, Filter
▾ (the page's chips in a popover under it), ⌕ and ⋯; the popovers are layers
(Back, Esc) that do not lock the page. Narrowed to 390: the same links are the
bottom tab bar again. At 390×844 (touch): the header has no box, the header
row is at most 56 px.

    python3 tools/desk_probe.py                     # playwright on the system python
    SHOTS=/some/dir python3 tools/desk_probe.py     # also keep screenshots
"""

import os
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layer_probe as lp  # noqa: E402

lp.PORT = int(os.environ.get("PROBE_PORT", "18495"))
lp.BASE = BASE = f"http://127.0.0.1:{lp.PORT}"
check, failures = lp.check, lp.failures
SHOTS = os.environ.get("SHOTS")


def shot(page, name):
    if SHOTS:
        page.screenshot(path=os.path.join(SHOTS, name))


def js(page, expr):
    return page.evaluate(expr)


def is_open(page, sel):
    return js(page, f"!!document.querySelector('{sel}.open')")


def go(page, url):
    page.goto(BASE + url)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(200)


def desk(page):
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    go(page, "/pens/")
    box = js(page, "(() => { const r = document.getElementById('hdr').getBoundingClientRect(); return [r.top, r.height]; })()")
    check("bar: at the top, 52 px", box == [0, 52])
    tabs = js(page, "[...document.querySelectorAll('#hdr nav.kit-tabs a')].filter(a => a.offsetParent).map(a => a.textContent.trim())")
    check("bar: six tabs", tabs == ["Desk", "Inkings", "Pens", "Inks", "History", "Records"])
    check("bar: Pens is lit", js(page, "document.querySelector('#hdr nav.kit-tabs .kit-tab[aria-current=page]').textContent.trim()") == "Pens")
    check(
        "bar: every control on one row",
        js(
            page,
            """(() => {
        const h = document.getElementById('hdr').getBoundingClientRect();
        return [...document.querySelectorAll('#hdr .db-brand, #hdr nav.kit-tabs a, #deskFilterBtn, #deskSearchBtn, #hdr .db-btn[data-menu-btn]')]
          .every(e => { const r = e.getBoundingClientRect(); return r.height > 0 && r.top >= h.top && r.bottom <= h.bottom; });
    })()""",
        ),
    )
    order = js(
        page,
        """['.db-brand', '#deskFilterBtn', '#deskSearchBtn', '#hdr .db-btn[data-menu-btn]']
        .map(s => document.querySelector(s).getBoundingClientRect().left)""",
    )
    check("bar: brand, then Filter, ⌕, ⋯ from left to right", order == sorted(order))
    check("bar: the tab bar is not fixed to the bottom", js(page, "getComputedStyle(document.querySelector('nav.kit-tabs')).position") == "static")
    check("no pill nav, no floating button", js(page, "!document.querySelector('.app-nav, #topbar')"))
    check("the chip row is folded", js(page, "getComputedStyle(document.getElementById('rotbar')).display") == "none")
    check("Filter names nothing while All is on", js(page, "document.querySelector('#deskFilterBtn b').textContent") == "")
    h = js(page, "document.querySelector('.page-head.hrow').getBoundingClientRect().height")
    check(f"header row ≤ 56 px ({h:.0f})", h <= 56)

    # Filter ▾: the chips under the button, no lock, a history entry
    url = page.url
    page.click("#deskFilterBtn")
    page.wait_for_timeout(300)
    check("filter: open", is_open(page, "#deskFilter"))
    check("filter: the page is not locked", not lp.lock(page))
    check("filter: a history entry", (js(page, "history.state") or {}).get("kitLayer") == 1)
    pop = js(
        page,
        "(() => { const p = document.getElementById('deskFilter').getBoundingClientRect(), b = document.getElementById('deskFilterBtn').getBoundingClientRect(); return [p.top - b.bottom, Math.round(p.right - b.right), p.left >= 0]; })()",
    )
    check("filter: under its button, right edges in line", 0 < pop[0] < 20 and pop[1] == 0 and pop[2])
    n_chips = js(page, "document.querySelectorAll('#deskFilter .db-chips > button').length")
    check("filter: the same chips", n_chips == js(page, "document.querySelectorAll('#rotbar a').length") and n_chips > 1)
    shot(page, "desk-pens-filter.png")
    page.go_back()
    page.wait_for_timeout(400)
    check("filter: Back closes it, stays on the page", not is_open(page, "#deskFilter") and page.url == url)
    page.click("#deskFilterBtn")
    page.wait_for_timeout(300)
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    check("filter: Esc closes it", not is_open(page, "#deskFilter"))
    page.click("#deskFilterBtn")
    page.wait_for_timeout(300)
    page.mouse.click(700, 600)
    page.wait_for_timeout(300)
    check("filter: a click outside closes it", not is_open(page, "#deskFilter"))
    # a chip in the popover filters the page as the real chip does
    page.click("#deskFilterBtn")
    page.wait_for_timeout(300)
    n0 = js(page, "history.length")
    page.locator("#deskFilter .db-chips > button").nth(2).click()
    page.wait_for_timeout(1200)
    check("filter: a chip filters (URL)", "rot=" in page.url)
    label = js(page, "document.querySelector('#deskFilterBtn b').textContent")
    check(f"filter: the button names it ({label!r})", label.startswith("Priority") or label in ("Other", "Defunct"))
    check("filter: no layer left open", not (js(page, "history.state") or {}).get("kitLayer"))
    # The kit's filters: a tap replaces the entry (kit README §4 "Filters"), so
    # Back leaves the list rather than walking through its chips.
    check("filter: a chip replaces the history entry", js(page, "history.length") == n0)
    go(page, "/pens/")

    # A tab: hx-boost swaps the page, the bar follows.
    page.click("#hdr nav.kit-tabs a[href='/inks/']")
    page.wait_for_url("**/inks/", timeout=8000)
    page.wait_for_timeout(800)
    check("tab: Inks is lit after the swap", js(page, "document.querySelector('#hdr nav.kit-tabs .kit-tab[aria-current=page]').textContent.trim()") == "Inks")
    check(
        "tab: Filter now stands for the ink filters",
        js(page, "document.getElementById('deskFilterBtn') && getComputedStyle(document.querySelector('#main [data-fold]')).display") == "none",
    )
    page.click("#deskFilterBtn")
    page.wait_for_timeout(300)
    check("tab: the popover heads Ink filters", js(page, "document.querySelector('#deskFilter .db-pop-head').textContent") == "Ink filters")
    page.locator("#deskFilter button:has(.kit-chip-dot)").first.click()
    page.wait_for_timeout(1200)
    check("inks: a colour filters", "color=" in page.url)
    check("inks: the button names the colour", js(page, "document.querySelector('#deskFilterBtn b').textContent") != "")
    go(page, "/history/")
    check("history: no chip row, no Filter", js(page, "!document.getElementById('deskFilterBtn')"))

    # ⌕: the menu's search, lent to the popover
    page.click("#deskSearchBtn")
    page.wait_for_timeout(300)
    check("search: open, field focused", is_open(page, "#deskSearch") and js(page, "document.activeElement.id") == "menuSearchInput")
    page.keyboard.type("blue")
    page.keyboard.press("Enter")
    page.wait_for_url("**/search/?q=blue", timeout=8000)
    page.wait_for_load_state("networkidle")
    check("search: Enter searches", "/search/?q=blue" in page.url)
    check("search: the field is back in the menu", js(page, "document.getElementById('menuSearchForm').parentNode.id") == "menuPanel")

    # ⋯: the menu under it, without the places the bar has as tabs
    page.click("#hdr .db-btn[data-menu-btn]")
    page.wait_for_timeout(300)
    check("menu: open", js(page, "document.getElementById('menuPanel').classList.contains('open')"))
    m = js(page, "(() => { const p = document.getElementById('menuPanel').getBoundingClientRect(); return [p.top, p.bottom < innerHeight]; })()")
    check("menu: under the bar", 52 < m[0] < 70 and m[1])
    check("menu: no tabs in it", js(page, "[...document.querySelectorAll('#menuPanel [data-tab]')].every(a => !a.offsetParent)"))
    check("menu: no second search in it", js(page, "!document.querySelector('#menuPanel .menu-search').offsetParent"))
    check("menu: not locked", not lp.lock(page))
    shot(page, "desk-menu.png")
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)

    # A record's verbs are labelled buttons on a desk.
    go(page, "/pens/")
    href = js(
        page, "[...document.querySelectorAll('#main a[href^=\"/pens/\"]')].map(a => a.getAttribute('href')).find(h => /^\\/pens\\/\\d+\\/$/.test(h))"
    )
    go(page, href)
    verbs = js(
        page,
        "[...document.querySelectorAll('.detail-actions .overflow-panel a, .detail-actions .overflow-panel button')].filter(e => e.offsetParent).map(e => e.textContent.trim())",
    )
    check(f"pen: verbs as buttons ({verbs})", "Edit pen" in verbs and "Delete pen" in verbs)
    check("pen: no ⋯ for them", js(page, "!document.querySelector('.detail-actions [data-overflow-btn]').offsetParent"))
    shot(page, "desk-pen.png")

    # Narrow the window: the phone's shape, the same markup.
    go(page, "/pens/")
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(400)
    check("narrow: header has no box", js(page, "document.getElementById('hdr').getBoundingClientRect().height") == 0)
    tb = js(
        page,
        "(() => { const r = document.querySelector('nav.kit-tabs').getBoundingClientRect(); return [getComputedStyle(document.querySelector('nav.kit-tabs')).position, Math.round(r.bottom)]; })()",
    )
    check(f"narrow: the tab bar is at the bottom ({tb})", tb == ["fixed", 844])
    check(
        "narrow: the chips are back, Filter gone",
        js(page, "getComputedStyle(document.getElementById('rotbar')).display") != "none" and js(page, "!document.getElementById('deskFilterBtn')"),
    )
    check("narrow: History is not a tab", js(page, "!document.querySelector('nav.kit-tabs [data-desk]').offsetParent"))
    page.set_viewport_size({"width": 1440, "height": 900})
    page.wait_for_timeout(400)
    check("wide again: Filter is back", js(page, "!!document.getElementById('deskFilterBtn')"))
    check("desk: no page errors", not errors)
    if errors:
        print("   ", errors)


def phone(page):
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    for url in ("/dashboard/", "/pens/", "/inks/", "/usages/"):
        go(page, url)
        h = js(page, "document.querySelector('.page-head.hrow').getBoundingClientRect().height")
        check(f"phone {url}: header row ≤ 56 px ({h:.0f})", h <= 56)
        cut = js(
            page, "(() => { const s = document.querySelector('.hstate, .page-head.hrow .dash-line'); return s.scrollWidth > s.clientWidth + 1; })()"
        )
        check(f"phone {url}: the state line fits", not cut)
        check(f"phone {url}: no sideways scroll", js(page, "document.documentElement.scrollWidth <= innerWidth"))
    check("phone: header has no box", js(page, "document.getElementById('hdr').getBoundingClientRect().height") == 0)
    check(
        "phone: five tabs",
        js(
            page,
            "[...document.querySelectorAll('nav.kit-tabs .kit-tab')].filter(e => e.offsetParent !== null || getComputedStyle(e).display !== 'none').length",
        )
        == 5,
    )
    page.click("nav.kit-tabs [data-menu-btn]")
    page.wait_for_timeout(300)
    check(
        "phone: More opens the menu with its search",
        js(
            page,
            "document.getElementById('menuPanel').classList.contains('open') && !!document.querySelector('#menuPanel .menu-search').offsetParent",
        ),
    )
    check("phone: the menu lists History", js(page, "!!document.querySelector('#menuPanel a[href=\"/history/\"]').offsetParent"))
    shot(page, "phone-menu.png")
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    go(page, "/pens/")
    shot(page, "phone-pens.png")
    check("phone: no page errors", not errors)
    if errors:
        print("   ", errors)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        proc, sess = lp.start(tmp)
        try:
            with sync_playwright() as p:
                b = p.chromium.launch()
                ctx = b.new_context(viewport={"width": 1440, "height": 900})
                ctx.add_cookies([{"name": "sessionid", "value": sess, "url": BASE}])
                desk(ctx.new_page())
                ctx.close()
                ctx = b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
                ctx.add_cookies([{"name": "sessionid", "value": sess, "url": BASE}])
                phone(ctx.new_page())
                ctx.close()
                b.close()
        finally:
            proc.terminate()
            proc.wait()
    print(f"\n{len(failures)} failed" if failures else "\nall passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
