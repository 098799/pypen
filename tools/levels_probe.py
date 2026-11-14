"""Ink left (README "Ink left") in a phone browser, on a copy of the newest backup.

Headless Chromium at 390×844 (touch) against a throwaway copy on a spare port, a
session made in the copy. It writes, in the copy only: looks at a bottle, marks a
sample used up from the desk and takes it back. Never point it at the live site
(tools/live_walk.py reads).

    PLAYWRIGHT_BROWSERS_PATH=/home/tgrining/.cache/ms-playwright python3 tools/levels_probe.py
    SHOTS=dir   phone shots of each step
"""

import os
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layer_probe as lp  # noqa: E402

lp.PORT = int(os.environ.get("PROBE_PORT", "18533"))
lp.BASE = BASE = f"http://127.0.0.1:{lp.PORT}"
# A worktree has no venv of its own: the checkout's.
if not lp.PY.exists():
    lp.PY = Path("/home/tgrining/pypen/.devvenv/bin/python")
BACKUPS = Path("/home/tgrining/.local/share/vps-backups/pypen")
SHOTS = os.environ.get("SHOTS")
failures = []


def check(name, cond, more=""):
    print(("ok   " if cond else "FAIL ") + name + (f"  {more}" if more != "" and not cond else ""))
    if not cond:
        failures.append(name)


def settle(page, ms=300):
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(ms)


def shot(page, name):
    if SHOTS:
        page.screenshot(path=os.path.join(SHOTS, name + ".png"))


def go(page, path):
    r = page.goto(BASE + path)
    settle(page)
    check(f"{path}: 200", r.status == 200, r.status)
    check(f"{path}: no sideways scroll", page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))


def to(page, sel):
    page.evaluate(f"document.querySelector({sel!r}).scrollIntoView({{block: 'start'}}); window.scrollBy(0, -70)")
    page.wait_for_timeout(200)


def walk(page):
    js = page.evaluate
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    # 1. The cupboard: a level line on every open card, the list says what is left.
    go(page, "/inks/")
    check("wall: a level line on the cards", page.locator(".card-ink .lvl").count() >= 20)
    shot(page, "inks-wall")
    go(page, "/inks/?sort=left&view=list")
    rows = page.locator(".ink-row-nx")
    check("list: rows say what is left", "ml left" in rows.first.inner_text() or "fill" in rows.first.inner_text())
    check("list: Least left is the sort", js("document.querySelector('select[name=sort]').value") == "left")
    shot(page, "inks-least-left")
    href = rows.first.locator("h3 a").get_attribute("href")

    # 2. The ink page: the bottle and a look at it.
    go(page, href)
    check("ink: the bottle", page.locator(".level-plate .bottle").count() == 1)
    to(page, "#level")
    shot(page, "ink-level")
    page.locator("#level summary", has_text="I looked at it").tap()
    page.wait_for_timeout(250)
    check("ink: the look opens in place", page.locator("#level .look-sheet").is_visible())
    check("ink: six looks", page.locator("#level .look-btns .vbtn").count() == 6)
    check(
        "ink: the sheet fits the plate",
        js(
            "(() => { const s = document.querySelector('#level .look-sheet').getBoundingClientRect(); const c = document.querySelector('#level').getBoundingClientRect(); return s.left >= c.left && s.right <= c.right + 0.5; })()"
        ),
    )
    shot(page, "ink-look-open")
    page.locator("#level .vbtn", has_text="½").tap()
    settle(page, 600)
    check("ink: back on the ink", page.url.split("#")[0].endswith(href), page.url)
    body = js("document.body.innerText")
    check("ink: the toast says what is left", "ml left." in body)
    check("ink: the look is remembered", "You looked on" in page.locator("#level").inner_text())
    check("ink: the gauge is at a half", "--lvl: 50%" in (page.locator("#level .bottle").get_attribute("style") or ""))
    js("window.kitTheme && kitTheme.set('dark')")
    go(page, href)
    to(page, "#level")
    shot(page, "ink-level-dark")
    js("window.kitTheme && kitTheme.set('auto')")

    # 3. The desk: Running low, Used up in one tap, and Undo.
    go(page, "/dashboard/")
    low = page.locator("#lowH").locator("xpath=ancestor::section")
    n = low.locator(".row").count()
    check("desk: Running low lists some", n >= 1, n)
    to(page, "#lowH")
    shot(page, "desk-running-low")
    name = low.locator(".row-t a").first.inner_text()
    low.locator("button", has_text="Used up").first.tap()
    settle(page, 600)
    check("desk: stays on the desk", page.url.endswith("/dashboard/"), page.url)
    check("desk: the toast says used up", "used up." in js("document.body.innerText"))
    check("desk: the row is gone", name not in page.locator("#lowH").locator("xpath=ancestor::section").inner_text())
    undo = page.locator("#kit-toast button:not([hidden])", has_text="Undo")
    check("desk: the toast offers Undo", undo.count() == 1)
    if undo.count():
        undo.first.tap()
        settle(page, 800)
        check("desk: Undo brings it back", name in page.locator("#lowH").locator("xpath=ancestor::section").inner_text())

    # 4. Stats, suink, a pen.
    go(page, "/stats/cupboard/")
    check("cupboard: Ink drunk", page.locator("#inkLeft .bar-col").count() >= 3)
    to(page, "#inkLeft")
    shot(page, "stats-ink-drunk")
    go(page, "/suink/")
    check("suink: what is left", page.locator(".turns-left").count() >= 20)
    go(page, "/pens/")
    pen = page.locator("#penContentBody a[href^='/pens/']").first.get_attribute("href")
    go(page, pen)
    check("pen: ink drunk", "ml of ink" in page.locator(".tally").inner_text())
    go(page, pen + "edit/")
    check("pen form: the fill size", page.locator("input[name=fill_ml]").count() == 1)
    check(f"no page error {errors[:3]}", not errors)


def main():
    src = sorted(BACKUPS.glob("pypen-*.db"), key=lambda p: p.stat().st_mtime)[-1]
    with tempfile.TemporaryDirectory() as tmp:
        proc, sess = lp.start(tmp, src)
        try:
            with sync_playwright() as p:
                b = p.chromium.launch()
                ctx = b.new_context(
                    viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True, service_workers="block"
                )
                ctx.add_cookies([{"name": "sessionid", "value": sess, "url": BASE}])
                walk(ctx.new_page())
                b.close()
        finally:
            proc.terminate()
            proc.wait()
    print("all passed" if not failures else f"{len(failures)} FAILED: {failures}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
