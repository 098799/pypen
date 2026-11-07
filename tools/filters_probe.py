"""The kit's list controls with htmx, in a phone browser (AUDIT pass 7, kit README §4).

Headless Chromium at 390×844 against a throwaway copy of a database (the newest backup, or
PROBE_DB) on a spare port, a session made in the copy, every non-GET refused: never the live data.

    PLAYWRIGHT_BROWSERS_PATH=/home/tgrining/.cache/ms-playwright python tools/filters_probe.py
    SHOTS=dir  ... also saves the screens, dark and light.

Checks: keystrokes and chips add no history entry; × brings the list back; a word typed goes
with a chip; one sort does not reload; no ?q= and no default in the address; the menu search
waits for Enter; the Gantt's rotation survives a reload; the desk's Filter ▾ still works.
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layer_probe as lp  # noqa: E402

lp.PORT = int(os.environ.get("PROBE_PORT", "18497"))
lp.BASE = BASE = f"http://127.0.0.1:{lp.PORT}"
BACKUPS = Path("/home/tgrining/.local/share/vps-backups/pypen")
SHOTS = os.environ.get("SHOTS")
failures = []

MEASURE = """() => {
  const lum = c => { const m = c.match(/[\\d.]+/g).map(Number), f = v => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4 }; return .2126 * f(m[0]) + .7152 * f(m[1]) + .0722 * f(m[2]) };
  const cr = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + .05) / (Math.min(x, y) + .05) };
  const chips = [...document.querySelectorAll('.kit-chip')].filter(c => c.offsetParent);
  const rows = [...document.querySelectorAll('.kit-chips')].filter(c => c.offsetParent);
  const on = chips.find(c => c.matches('[aria-current=true],[aria-pressed=true]')), off = chips.find(c => !c.matches('[aria-current=true],[aria-pressed=true]'));
  const r = {chips: chips.length, h: Math.min(...chips.map(c => c.getBoundingClientRect().height)), row: Math.min(...rows.map(c => c.getBoundingClientRect().height)), over: document.documentElement.scrollWidth - innerWidth};
  if (on) { const s = getComputedStyle(on); r.on = +cr(s.backgroundColor, s.color).toFixed(2); r.onbg = s.backgroundColor; }
  if (off) { const s = getComputedStyle(off); r.off = +cr(s.backgroundColor, s.color).toFixed(2); r.offbg = s.backgroundColor; }
  r.boxes = [...document.querySelectorAll('.kit-search input,.kit-sort select')].filter(i => i.offsetParent).map(i => [parseFloat(getComputedStyle(i).fontSize), i.getBoundingClientRect().height, !!(i.getAttribute('aria-label') || i.closest('label'))]);
  return r }"""


def check(name, cond, more=""):
    print(("ok   " if cond else "FAIL ") + name + (f"  {more}" if more != "" and not cond else ""))
    if not cond:
        failures.append(name)


def settle(page, ms=500):
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(ms)


def path(page):
    return page.url.replace(BASE, "")


def on_chips(page):
    return page.evaluate("[...document.querySelectorAll('#main .kit-chip[aria-current=true]')].map(c => c.textContent.trim().replace(/\\s+/g,' '))")


def measure(page, where, theme):
    m = page.evaluate(MEASURE)
    print(f"     {where} {theme}: {json.dumps(m)}")
    check(f"{where} {theme}: chips 32, row 44", m["h"] >= 32 and m["row"] >= 44, m)
    if "on" in m:
        check(f"{where} {theme}: picked chip ≥ 4.5:1 and filled differently", m["on"] >= 4.5 and m["onbg"] != m.get("offbg"), m)
    if "off" in m:
        check(f"{where} {theme}: other chips ≥ 4.5:1", m["off"] >= 4.5, m)
    check(f"{where} {theme}: boxes 16 px, 44 px, named", all(b[0] >= 16 and b[1] >= 44 and b[2] for b in m["boxes"]), m["boxes"])
    check(f"{where} {theme}: nothing wider than the phone", m["over"] <= 0, m["over"])


def screens(page, theme):
    for name, url in (("inks", "/inks/?color=Blue"), ("pens", "/pens/?rot=p1"), ("usages", "/usages/?q=pilot"),
                      ("search", "/search/?q=blue&samples=1"), ("gantt", "/history/gantt/?rot=p1"),
                      ("pub", "/pub/inks/"), ("wall", "/pub/inks/wall/")):
        page.goto(BASE + url + ("&" if "?" in url else "?") + "theme=" + theme)
        page.evaluate(f"kitTheme.set({theme!r})")
        settle(page, 300)
        measure(page, name, theme)
        if SHOTS:
            page.screenshot(path=os.path.join(SHOTS, f"pypen-{name}-{theme}.png"))


def run(page):
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

    # ---- pens: keystrokes, ×, a chip, a word with a chip
    page.goto(BASE + "/pens/")
    settle(page)
    n0 = page.evaluate("history.length")
    page.evaluate("window.__same = 1")
    page.locator("#penQ").type("pilot", delay=60)
    settle(page, 700)
    check("pens: 5 letters add no history entry", page.evaluate("history.length") == n0)
    check("pens: the word is in the address", "q=pilot" in page.url, page.url)
    check("pens: no reload", page.evaluate("window.__same") == 1)
    all_rows = page.evaluate("document.querySelectorAll('#penContentBody [data-listnav-item]').length")
    page.tap("#penFilterForm .kit-search-x")
    settle(page, 700)
    check("pens: × empties the address", "q=" not in page.url, page.url)
    check("pens: × brings the list back", page.evaluate("document.querySelectorAll('#penContentBody [data-listnav-item]').length") >= all_rows)
    chip = page.locator("#rotbar .kit-chip[data-navval=p1]")
    chip.tap()
    settle(page)
    check("pens: a chip adds no entry", page.evaluate("history.length") == n0)
    check("pens: the chip is on", "rot=p1" in page.url and chip.get_attribute("aria-current") == "true" and len(on_chips(page)) == 1, on_chips(page))
    check("pens: no ?rot= on All", "rot" not in page.locator("#rotbar .kit-chip").first.get_attribute("href"))
    # a word and straight away a chip: both, whichever answer comes last
    page.locator("#penQ").type("pil", delay=10)
    page.locator("#rotbar .kit-chip[data-navval=p0]").tap()
    settle(page, 900)
    check("pens: the word goes with the chip", "q=pil" in page.url and "rot=p0" in page.url, page.url)
    check("pens: the box still has it", page.input_value("#penQ") == "pil")
    page.goto(BASE + "/pens/?q=pil&rot=p0")
    settle(page)
    check("pens: back on the same row after a reload", page.locator("#rotbar .kit-chip[data-navval=p0]").get_attribute("aria-current") == "true")

    # ---- inks: colour, sort, clear
    page.goto(BASE + "/inks/")
    settle(page)
    page.evaluate("window.__same = 1")
    n0 = page.evaluate("history.length")
    last = page.locator("#inkFilters a[data-color]").last
    last.scroll_into_view_if_needed()
    last.tap()
    settle(page)
    col = page.locator("#inkFilters a[data-color][aria-current=true]")
    check("inks: the colour is on, no entry added", col.count() == 1 and page.evaluate("history.length") == n0, on_chips(page))
    box = col.bounding_box()
    check("inks: the picked colour stays on the screen", box and 0 <= box["x"] and box["x"] + box["width"] <= 390, box)
    page.select_option("#inkFilterForm ~ .kit-sort select, .kit-sort select", index=1)
    settle(page)
    check("inks: a sort keeps the colour, no reload", "sort=" in page.url and "color=" in page.url and page.evaluate("window.__same") == 1, page.url)
    check("inks: a sort adds no entry", page.evaluate("history.length") == n0)
    page.select_option(".kit-sort select", index=0)
    settle(page)
    check("inks: the default sort leaves the address", "sort" not in page.url, page.url)
    page.locator("#inkFilters .kit-chip-clear").tap()
    settle(page)
    check("inks: Clear empties it", path(page) == "/inks/", page.url)
    # the row is new after each swap: the kit's × and fade on it, as at load
    check("inks: no Clear when nothing is on", page.locator("#inkFilters .kit-chip-clear").count() == 0)
    page.locator("#inkQ").type("blue", delay=60)
    settle(page, 700)
    check("inks: search replaces", page.evaluate("history.length") == n0 and "q=blue" in page.url)
    page.locator(".vt-btn[data-view=grid]").tap()
    settle(page)
    check("inks: the view goes with the word", "q=blue" in page.url and "view=grid" in page.url, page.url)
    page.locator(".vt-btn[data-view=list]").tap()
    settle(page)
    check("inks: back to the list, the word stays", "q=blue" in page.url and "view" not in page.url, page.url)
    check("inks: its aria-current", page.locator(".vt-btn[data-view=list]").get_attribute("aria-current") == "true")

    # ---- search
    page.goto(BASE + "/search/")
    settle(page)
    page.evaluate("window.__same = 1")
    n0 = page.evaluate("history.length")
    page.locator("#searchQ").type("blue", delay=60)
    settle(page, 700)
    check("search: only ?q=", path(page) == "/search/?q=blue", page.url)
    page.locator("#searchFilters label:has(input[value=inks])").tap()
    settle(page)
    check("search: a type chip", "type=inks" in page.url and page.locator("#searchFilters label:has(input[value=inks])").get_attribute("aria-current") == "true", page.url)
    page.locator("#searchFilters label:has(input[name=samples])").tap()
    settle(page)
    check("search: a toggle chip", "samples=1" in page.url and page.locator("#searchFilters label:has(input[name=samples])").get_attribute("aria-current") == "true", page.url)
    page.select_option(".kit-sort select", "recent")
    settle(page)
    check("search: a sort", "sort=recent" in page.url and "samples=1" in page.url and page.evaluate("window.__same") == 1, page.url)
    page.select_option(".kit-sort select", "alpha")
    settle(page)
    page.locator("#searchFilters label:has(input[value=both])").tap()
    settle(page)
    page.locator("#searchFilters label:has(input[name=samples])").tap()
    settle(page)
    check("search: defaults leave the address", path(page) == "/search/?q=blue", page.url)
    page.tap("#searchForm .kit-search-x")
    settle(page, 700)
    check("search: × empties it", path(page) == "/search/", page.url)
    check("search: no entry added", page.evaluate("history.length") == n0)
    check("search: not busy for ever", page.locator("#searchForm[aria-busy]").count() == 0)

    # ---- the menu's search
    page.goto(BASE + "/pens/")
    settle(page)
    page.locator("nav.kit-tabs [data-menu-btn]").tap()
    page.wait_for_timeout(300)
    page.locator("#menuSearchInput").type("pilot", delay=120)
    page.wait_for_timeout(500)
    check("menu: typing stays on the page", path(page) == "/pens/", page.url)
    if SHOTS:
        page.screenshot(path=os.path.join(SHOTS, "pypen-menu.png"))
    page.keyboard.press("Enter")
    settle(page)
    check("menu: Enter searches", "/search/?q=pilot" in page.url, page.url)
    page.go_back()
    settle(page)
    check("menu: Back leaves the search", path(page).startswith("/pens/"), page.url)

    # ---- the Gantt
    page.goto(BASE + "/history/gantt/")
    settle(page)
    chips = page.locator(".kit-chip.rot-filter[data-rot=p1]")
    chips.tap()
    page.wait_for_timeout(200)
    check("gantt: the rotation in the address", "rot=p1" in page.url and chips.get_attribute("aria-pressed") == "true", page.url)
    hidden = page.evaluate("document.querySelectorAll('.gantt-row.hidden-row').length")
    check("gantt: rows hidden", hidden > 0)
    page.reload()
    settle(page)
    check("gantt: a reload keeps it", page.locator(".kit-chip.rot-filter[data-rot=p1]").get_attribute("aria-pressed") == "true"
          and page.evaluate("document.querySelectorAll('.gantt-row.hidden-row').length") == hidden)
    page.locator(".kit-chip.rot-filter[data-rot='']").tap()
    page.wait_for_timeout(200)
    check("gantt: All leaves the address", "rot" not in page.url, page.url)

    # ---- the wall (plain links)
    page.goto(BASE + "/pub/inks/wall/")
    settle(page)
    n0 = page.evaluate("history.length")
    page.locator(".kit-chips .kit-chip").first.tap()
    settle(page)
    check("wall: a chip replaces", "samples=0" in page.url and page.evaluate("history.length") == n0, page.url)
    check("wall: the chip is off", page.locator(".kit-chips .kit-chip").first.get_attribute("aria-current") is None)

    check("no page error", not errors, errors[:3])


def desk(page):
    page.goto(BASE + "/inks/?color=Blue")
    settle(page)
    check("desk: Filter ▾ names the colour", "Blue" in page.locator("#deskFilterBtn b").text_content())
    check("desk: the row is folded", page.evaluate("getComputedStyle(document.getElementById('inkFilters')).display") == "none")
    page.click("#deskFilterBtn")
    page.wait_for_timeout(300)
    check("desk: the same chips", page.locator("#deskFilter button.kit-chip").count() == page.locator("#inkFilters a").count())
    check("desk: the picked one shows it", page.locator("#deskFilter button.kit-chip[aria-current=true]").count() == 1)
    if SHOTS:
        page.screenshot(path=os.path.join(SHOTS, "pypen-desk-filter.png"))
    page.locator("#deskFilter button:has(.kit-chip-dot)").first.click()
    settle(page)
    check("desk: a chip there filters", "color=" in page.url, page.url)
    page.goto(BASE + "/pens/")
    settle(page)
    page.click("#deskFilterBtn")
    page.wait_for_timeout(300)
    page.locator("#deskFilter button.kit-chip").nth(1).click()
    settle(page)
    check("desk: a rotation there filters", "rot=" in page.url and page.locator("#deskFilterBtn b").text_content() != "", page.url)


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
                run(ctx(**phone).new_page())
                for theme in ("dark", "light"):
                    screens(ctx(color_scheme=theme, **phone).new_page(), theme)
                desk(ctx(viewport={"width": 1440, "height": 900}).new_page())
                b.close()
        finally:
            proc.terminate()
            proc.wait()
    print("all passed" if not failures else f"{len(failures)} FAILED: {failures}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
