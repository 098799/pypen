"""The paged lists in a phone browser (PYPEN-7, kit README §14).

Headless Chromium at 390×844 (touch) against a throwaway copy of a database
(the newest backup in ~/.local/share/vps-backups/pypen, or PROBE_DB) and of
its photos, on a spare port, DEBUG on, a session made in the copy: never the
live data.

    PLAYWRIGHT_BROWSERS_PATH=/home/tgrining/.cache/ms-playwright python3 tools/lists_probe.py
    SHOTS=dir  ... also saves the screens; WHATSNEW=1 writes the What's new shot.

Checks: 50 rows a page; Load more appends the next 50 and the group a page
starts inside keeps one heading; a double tap loads once; the last page drops
the button; the search box puts q in the URL and survives a reload; /search/
goes on with one kind; nothing wider than the phone; no page error.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layer_probe as lp  # noqa: E402

BACKUPS = Path("/home/tgrining/.local/share/vps-backups/pypen")
SHOTS = os.environ.get("SHOTS")
WHATSNEW = lp.APP / "dpypen" / "items" / "static" / "items" / "whatsnew" / "2026-11-01-inkings-search.png"
failures = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def shot(page, name):
    if SHOTS:
        page.screenshot(path=os.path.join(SHOTS, name))


def source_db():
    if os.environ.get("PROBE_DB"):
        return Path(os.environ["PROBE_DB"])
    return max(BACKUPS.glob("pypen-*.db"), key=lambda p: p.stat().st_mtime)


def rows(page):
    return page.evaluate("document.querySelectorAll('#main [data-listnav-item]').length")


def heads(page):
    return page.evaluate("[...document.querySelectorAll('#main [data-more-head] h3')].map(h => h.textContent.trim())")


def settle(page, ms=500):
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(ms)


def no_sideways(page, where):
    check(f"{where}: nothing wider than the phone", page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))


def run(page):
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    asks = []
    page.on("request", lambda r: asks.append(r.url) if r.headers.get("x-pypen-more") == "1" else None)

    # /pens/: three pages of rotation groups.
    page.goto(lp.BASE + "/pens/")
    settle(page)
    total = int(page.locator("#rotbar .kit-chip").first.locator("b").text_content())
    check(f"pens: the first page holds 50 of {total}", rows(page) == min(50, total))
    first_heads = heads(page)
    shot(page, "pens.png")
    btn = page.locator("a[data-more]")
    check("pens: Load more is there", btn.count() == 1)
    btn.dispatch_event("click")
    btn.dispatch_event("click")  # a double tap
    settle(page)
    check("pens: a double tap loads once", len(asks) == 1)
    check("pens: Load more appends 50", rows(page) == min(100, total))
    hs = heads(page)
    check(f"pens: no heading twice {hs}", len(hs) == len(set(hs)))
    check("pens: the first headings stay first", hs[: len(first_heads)] == first_heads)
    check("pens: the count runs from the first row", page.locator(".more-count").first.text_content().startswith("1–"))
    while page.locator("a[data-more]").count():
        page.locator("a[data-more]").click()
        settle(page, 300)
    check(f"pens: all {total} after the last page", rows(page) == total)
    check("pens: no button after the last page", page.locator("a[data-more]").count() == 0)
    hs = heads(page)
    check(f"pens: every group once {hs}", len(hs) == len(set(hs)))
    no_sideways(page, "pens")

    page.goto(lp.BASE + "/pens/?view=grid")
    settle(page)
    page.locator("a[data-more]").click()
    settle(page)
    check("pens grid: Load more appends tiles", rows(page) == 100 or rows(page) == total)
    no_sideways(page, "pens grid")

    # /inks/: the colour groups.
    page.goto(lp.BASE + "/inks/?samples=1&used=1")
    settle(page)
    check("inks: 50 rows", rows(page) == 50)
    page.locator("a[data-more]").click()
    settle(page)
    hs = page.evaluate("[...document.querySelectorAll('#main .group-head h3')].map(h => h.textContent.trim())")
    check(f"inks: every colour once {hs}", len(hs) == len(set(hs)))
    no_sideways(page, "inks")

    # /usages/: the search box, its state in the URL.
    page.goto(lp.BASE + "/usages/")
    settle(page)
    check("inkings: 50 past rows", page.evaluate("document.querySelectorAll('#main .list [data-listnav-item]').length") == 50)
    shot(page, "inkings.png")
    page.locator("#usageQ").click()
    page.locator("#usageQ").type("pilot blue", delay=40)
    page.wait_for_timeout(900)
    settle(page)
    check("inkings: q is in the URL", "q=pilot+blue" in page.url or "q=pilot%20blue" in page.url)
    marks = page.evaluate("document.querySelectorAll('#main mark').length")
    check(f"inkings: the words are marked ({marks})", marks > 0)
    if os.environ.get("WHATSNEW"):
        page.evaluate("document.activeElement && document.activeElement.blur()")
        page.wait_for_timeout(300)
        page.screenshot(path=str(WHATSNEW))
        from PIL import Image  # 128 colours: the kit's 150 KB cap, the swatches kept

        Image.open(WHATSNEW).convert("RGB").quantize(128, method=Image.Quantize.FASTOCTREE,
                                                     dither=Image.Dither.NONE).save(WHATSNEW, optimize=True)
        print("wrote", WHATSNEW)
    shot(page, "inkings-search.png")
    page.reload()
    settle(page)
    check("inkings: a reload keeps the search", page.locator("#usageQ").input_value() == "pilot blue")
    no_sideways(page, "inkings")

    # /search/: both kinds, then Load more goes on with one.
    page.goto(lp.BASE + "/search/?q=e")
    settle(page)
    n = page.evaluate("document.querySelectorAll('[data-more-host=\"search-pens\"] [data-listnav-item]').length")
    check("search: 20 pens first", n == 20)
    page.locator('[data-more-host="search-pens"] a[data-more]').click()
    settle(page)
    n2 = page.evaluate("document.querySelectorAll('[data-more-host=\"search-pens\"] [data-listnav-item]').length")
    check(f"search: Load more adds pens ({n2})", n2 > 20)
    check("search: the inks stay", page.evaluate("document.querySelectorAll('[data-more-host=\"search-inks\"] [data-listnav-item]').length") == 20)
    no_sideways(page, "search")

    check(f"no page error {errors}", not errors)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        media = Path(tmp) / "media"
        if (BACKUPS / "pen-media").is_dir():
            shutil.copytree(BACKUPS / "pen-media", media)
        proc, sess = lp.start(tmp, src=source_db())
        try:
            with sync_playwright() as p:
                b = p.chromium.launch()
                ctx = b.new_context(
                    viewport={"width": 390, "height": 844}, device_scale_factor=1, is_mobile=True, has_touch=True, service_workers="block"
                )
                ctx.add_cookies([{"name": "sessionid", "value": sess, "url": lp.BASE}])
                run(ctx.new_page())
                b.close()
        finally:
            proc.terminate()
            proc.wait()
    print("all passed" if not failures else f"{len(failures)} FAILED: {failures}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
