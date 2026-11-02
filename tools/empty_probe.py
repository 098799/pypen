"""The kit's empty block in a phone browser (KIT-EMPTY, kit README §4).

Headless Chromium at 390×844 against a throwaway copy of a database (the
newest backup, or PROBE_DB) on a spare port, as lists_probe.py: never the
live data. A route that answers 500 or drops the connection stands in for a
broken server.

    PLAYWRIGHT_BROWSERS_PATH=/home/tgrining/.cache/ms-playwright python3 tools/empty_probe.py
    SHOTS=dir  ... also saves the screens.

Checks: a live search that gets a 500 or no answer shows the kit's "could not
load" block in place of the old rows (the cause in words, Try again), and Try
again brings the rows back; a failed Load more says so under the button; a
no-match has Clear the search, and it works; nothing wider than the phone; no
page error.
"""

import os
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layer_probe as lp  # noqa: E402
import lists_probe as lsp  # noqa: E402

SHOTS = os.environ.get("SHOTS")
check, failures = lsp.check, lsp.failures


def PEN_Q(url):
    return "/pens/?" in url and "q=" in url


def SEARCH_Q(url):
    return "/search/?" in url and "q=" in url


def PEN_MORE(url):
    return "/pens/?" in url and "offset=" in url


def shot(page, name):
    if SHOTS:
        page.screenshot(path=os.path.join(SHOTS, name))


def bad(page):
    return page.evaluate("""(() => { const b = document.querySelector('#main .kit-empty[data-kind=bad]');
      return b ? {t: b.querySelector('.kit-empty-t').textContent, p: (b.querySelector('.kit-empty-p') || {}).textContent,
                  role: b.getAttribute('role'), btn: (b.querySelector('.kit-empty-b') || {}).textContent} : null; })()""")


def run(page):
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    # A live search on /pens/ that the server answers with a 500.
    page.goto(lp.BASE + "/pens/")
    lsp.settle(page)
    before = lsp.rows(page)
    page.route(PEN_Q, lambda r: r.fulfill(status=500, body="boom", content_type="text/html"))
    page.locator("#penQ").type("pilot", delay=30)
    page.wait_for_timeout(900)
    got = bad(page)
    check(f"pens 500: the bad block ({got})", bool(got) and "500" in (got["p"] or "") and got["role"] == "alert")
    check("pens 500: the old rows are gone", lsp.rows(page) == 0 and before > 0)
    shot(page, "pens-500.png")
    page.unroute(PEN_Q)
    page.locator("#main .kit-empty[data-kind=bad] .kit-empty-b").click()
    lsp.settle(page)
    check("pens 500: Try again brings the rows", lsp.rows(page) > 0 and bad(page) is None)

    # No answer at all on /search/.
    page.goto(lp.BASE + "/search/")
    lsp.settle(page)
    check("search: Type to search", page.locator("#main .kit-empty[data-kind=none]").count() == 1)
    page.route(SEARCH_Q, lambda r: r.abort())
    page.locator("#searchQ").type("blue", delay=30)
    page.wait_for_timeout(900)
    got = bad(page)
    check(f"search dropped: the bad block ({got})", bool(got) and "online" in (got["p"] or ""))
    page.unroute(SEARCH_Q)

    # A no-match and its way out.
    page.goto(lp.BASE + "/inks/?q=zzqqxx")
    lsp.settle(page)
    m = page.locator("#main .kit-empty[data-kind=match]")
    check("inks: a no-match block", m.count() == 1)
    shot(page, "inks-nomatch.png")
    m.locator(".kit-empty-b.go").click()
    lsp.settle(page)
    check("inks: Clear the search shows rows", lsp.rows(page) > 0 and "zzqqxx" not in page.url)

    # A failed Load more.
    page.goto(lp.BASE + "/pens/")
    lsp.settle(page)
    page.route(PEN_MORE, lambda r: r.fulfill(status=502, body="", content_type="text/html"))
    page.locator("a[data-more]").click()
    page.wait_for_timeout(700)
    f = page.locator("[data-more-fail] .kit-empty[data-kind=bad]")
    check("load more 502: said under the button", f.count() == 1 and "502" in f.text_content())
    check("load more 502: the button keeps its label", page.locator("a[data-more]").text_content().strip() == "Load more")
    shot(page, "more-502.png")
    page.unroute(PEN_MORE)
    f.locator(".kit-empty-b").click()
    lsp.settle(page)
    check("load more: Try again appends", lsp.rows(page) > 50 and page.locator("[data-more-fail]").count() == 0)
    lsp.no_sideways(page, "pens")
    check(f"no page error {errors}", not errors)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        proc, sess = lp.start(tmp, src=lsp.source_db())
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
