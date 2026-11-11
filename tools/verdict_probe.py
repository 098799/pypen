"""How it wrote (README "How it wrote") in a phone browser, on a copy of the newest backup.

Headless Chromium at 390×844 (touch) against a throwaway copy on a spare port, a
session made in the copy. It writes, in the copy only: finishes a fill with a
verdict and a note, says one later from the desk, filters the inkings by a chip.
Never point it at the live site (tools/live_walk.py reads).

    PLAYWRIGHT_BROWSERS_PATH=/home/tgrining/.cache/ms-playwright python3 tools/verdict_probe.py
    SHOTS=dir   phone shots of each step
"""

import os
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layer_probe as lp  # noqa: E402

lp.PORT = int(os.environ.get("PROBE_PORT", "18531"))
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


def walk(page):
    js = page.evaluate
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    # 1. Finish on the desk asks how it wrote, in place.
    go(page, "/dashboard/")
    card = page.locator("article.fill").first
    pen_href = card.locator(".fill-photo").get_attribute("href")
    card.locator("summary", has_text="Finish").tap()
    page.wait_for_timeout(250)
    check("desk: Finish opens the question", card.locator(".finish-sheet").is_visible())
    check("desk: three words", card.locator(".verdict-btns .vbtn").count() == 3)
    check(
        "desk: the sheet fits the card",
        js(
            "(() => { const s = document.querySelector('article.fill .finish-sheet').getBoundingClientRect(); const c = document.querySelector('article.fill').getBoundingClientRect(); return s.left >= c.left && s.right <= c.right + 0.5; })()"
        ),
    )
    card.scroll_into_view_if_needed()
    shot(page, "desk-finish-open")
    card.locator("input[name=note]").fill("wet, lovely shading")
    card.locator(".vbtn", has_text="Loved").tap()
    page.wait_for_url("**/dashboard/")
    settle(page, 600)
    check("desk: stays on the desk", page.url.endswith("/dashboard/"))
    check("desk: the toast says it", "loved" in js("document.body.innerText").lower())
    recent = page.locator("#recentH").locator("xpath=ancestor::section")
    check("desk: Just finished shows the word", recent.locator(".vsaid.is-loved").count() >= 1)
    check("desk: and the note", "wet, lovely shading" in recent.inner_text())

    # 2. Say one later, from the desk's Just finished.
    asks = recent.locator("form.vask")
    n = asks.count()
    check("desk: Just finished asks about the others", n >= 1, n)
    if n:
        js("document.querySelector('#recentH').scrollIntoView({block: 'start'}); window.scrollBy(0, -70)")
        page.wait_for_timeout(200)
        shot(page, "desk-just-finished")
        asks.first.locator(".vbtn", has_text="Fine").tap()
        settle(page, 600)
        check("desk: a later word lands", page.locator("#recentH").locator("xpath=ancestor::section").locator("form.vask").count() == n - 1)

    # 3. The pen's page: How it wrote, and its history rows.
    go(page, pen_href)
    check("pen: How it wrote", page.locator("#howItWrote").count() == 1)
    check("pen: Loved with its ink", page.locator(".vshelf-h.is-loved").count() == 1)
    js("document.querySelector('#howItWrote').scrollIntoView({block: 'start'}); window.scrollBy(0, -70)")
    page.wait_for_timeout(200)
    shot(page, "pen-how-it-wrote")
    js(
        "[...document.querySelectorAll('.sec-head h2')].find(h => h.textContent === 'History').scrollIntoView({block: 'start'}); window.scrollBy(0, -70)"
    )
    page.wait_for_timeout(200)
    shot(page, "pen-history")
    ink_href = page.locator(".vshelf-h.is-loved + .next-inks a").first.get_attribute("href")
    check("pen: a loved ink inks it again", "/usages/add/?pen=" in ink_href, ink_href)

    # 4. The pen page's Finish, on a pen inked now.
    go(page, "/dashboard/")
    other = page.locator("article.fill .fill-photo").first.get_attribute("href")
    go(page, other)
    page.locator(".rec-verbs summary", has_text="Finish this fill").tap()
    page.wait_for_timeout(250)
    check("pen: Finish this fill asks", page.locator(".rec-verbs .finish-sheet").is_visible())
    shot(page, "pen-finish-open")

    # 5. The inkings: chips, a chip filters, a note is found.
    go(page, "/usages/")
    check("inkings: the chips", page.locator("#verdictChips .kit-chip").count() >= 2)
    shot(page, "inkings-chips")
    page.locator("#verdictChips .kit-chip.is-loved").tap()
    page.wait_for_timeout(1200)
    settle(page)
    check("inkings: a chip filters", "verdict=loved" in page.url, page.url)
    check(
        "inkings: only loved rows",
        page.locator("#usageContentBody .rows .vsaid.is-loved").count() >= 1
        and page.locator("#usageContentBody .rows .row").count() == page.locator("#usageContentBody .rows .vsaid.is-loved").count(),
    )
    check("inkings: the chip is lit", page.locator("#verdictChips .kit-chip.is-loved[aria-current]").count() == 1)
    shot(page, "inkings-loved")
    page.locator("#verdictChips .kit-chip.is-loved").tap()
    page.wait_for_timeout(1200)
    settle(page)
    check("inkings: tapped again it turns off", "verdict=" not in page.url, page.url)
    go(page, "/usages/?q=shading")
    check("inkings: a note is found and marked", page.locator("#usageContentBody mark").count() >= 1)

    # 6. The picker and Stats.
    go(page, "/pick/?pen=" + pen_href.strip("/").split("/")[-1])
    # A loved ink just out of the pen has no rest yet, so it need not be in the top six (tests_verdicts holds the ranking).
    shot(page, "pick-loved")
    go(page, "/stats/pairs/")
    check("stats: How they wrote", page.locator("#howTheyWrote .vbar i").count() >= 1)
    js("document.querySelector('#howTheyWrote').scrollIntoView({block: 'start'}); window.scrollBy(0, -70)")
    page.wait_for_timeout(200)
    shot(page, "stats-how-they-wrote")

    # 7. The edit form, and dark.
    go(page, "/usages/?verdict=loved")
    page.locator("#usageContentBody a[href$='/edit/']").first.tap()
    page.wait_for_url("**/edit/")
    settle(page)
    check("form: the word is ticked", page.locator(".verdict-f input[value=loved]:checked").count() == 1)
    js("document.querySelector('.verdict-f').scrollIntoView({block: 'center'})")
    page.wait_for_timeout(200)
    shot(page, "form-verdict")
    js("window.kitTheme && kitTheme.set('dark')")
    go(page, pen_href)
    js("document.querySelector('#howItWrote').scrollIntoView({block: 'start'}); window.scrollBy(0, -70)")
    page.wait_for_timeout(200)
    shot(page, "pen-how-it-wrote-dark")
    js("window.kitTheme && kitTheme.set('auto')")
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
