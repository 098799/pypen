"""The install nudge (PYPEN-5, the kit's _install.html) in a real browser.

Headless Chromium at 390×844 (touch) against a throwaway copy of the local
database on a spare port (layer_probe's start-up): never the live data. The
browser's install offer is a made-up `beforeinstallprompt` event whose
prompt() counts its calls.

    python3 tools/install_probe.py                  # playwright on the system python
    SHOTS=/some/dir python3 tools/install_probe.py  # also keep screenshots
"""

import os
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layer_probe as lp  # noqa: E402

lp.PORT = int(os.environ.get("PROBE_PORT", "18497"))
lp.BASE = BASE = f"http://127.0.0.1:{lp.PORT}"
check, failures = lp.check, lp.failures
SHOTS = os.environ.get("SHOTS")
IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"

OFFER = """(outcome) => {
  const e = new Event('beforeinstallprompt', {cancelable: true});
  e.prompt = () => { window.prompted = (window.prompted || 0) + 1; };
  e.userChoice = Promise.resolve({outcome});
  window.dispatchEvent(e);
}"""
SHOWN = "!!document.querySelector('#installbar.on') && getComputedStyle(document.getElementById('installbar')).visibility === 'visible' && getComputedStyle(document.getElementById('installbar')).display !== 'none'"
STATE = "JSON.parse(localStorage.getItem('pypenInstallNudge') || '{}')"


def shot(page, name):
    if SHOTS:
        page.screenshot(path=os.path.join(SHOTS, name))


def load(page, path):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")


def run(ctx, page):
    js = page.evaluate

    load(page, "/prev/dashboard/")
    page.wait_for_timeout(4500)
    check("no offer: no bar", not js(SHOWN))
    js(OFFER, "dismissed")
    page.wait_for_timeout(1500)
    check("offer: not at once", not js(SHOWN))
    page.wait_for_timeout(3000)
    check("offer: the bar after ~4 s", js(SHOWN))
    r = js("document.getElementById('installbar').getBoundingClientRect().bottom")
    t = js("document.querySelector('nav.kit-tabs').getBoundingClientRect().top")
    check(f"above the tab bar ({r:.0f} <= {t:.0f})", r <= t)
    check("inside the phone", js("document.getElementById('installbar').getBoundingClientRect().right <= innerWidth"))
    shot(page, "installbar.png")

    # gives way to the kit's toast and the update toast
    js("kitToast('Saved')")
    page.wait_for_timeout(300)
    check("kit toast: the bar steps aside", not js(SHOWN))
    js("kitToast.close()")
    page.wait_for_timeout(300)
    check("kit toast gone: the bar is back", js(SHOWN))
    js("kitUpdate.show()")
    page.wait_for_timeout(300)
    check("update toast: the bar gives way", js("getComputedStyle(document.getElementById('installbar')).display") == "none")
    js("document.documentElement.classList.remove('kit-update-on')")

    # ✕: 14 days
    page.click(".kit-install-x")
    page.wait_for_timeout(500)
    st = js(STATE)
    days = (st.get("snoozeUntil", 0) - js("Date.now()")) / 864e5
    check(f"✕: hidden, 14 days ({days:.1f})", not js(SHOWN) and st.get("dismissed") == 1 and 13.9 < days < 14.1)
    load(page, "/prev/pens/")
    js(OFFER, "dismissed")
    page.wait_for_timeout(4500)
    check("snoozed: no bar", not js(SHOWN))

    # the snooze over: ✕ again is 60 days
    js("localStorage.setItem('pypenInstallNudge', JSON.stringify({dismissed: 1, snoozeUntil: 1}))")
    load(page, "/prev/pens/")
    js(OFFER, "dismissed")
    page.wait_for_timeout(4500)
    check("snooze over: the bar again", js(SHOWN))
    page.click(".kit-install-x")
    st = js(STATE)
    days = (st.get("snoozeUntil", 0) - js("Date.now()")) / 864e5
    check(f"second ✕: 60 days ({days:.1f})", st.get("dismissed") == 2 and 59.9 < days < 60.1)

    # Install: one prompt(), the Settings row lets go of the offer too
    js("localStorage.removeItem('pypenInstallNudge')")
    load(page, "/prev/pens/")
    js(OFFER, "accepted")
    page.wait_for_timeout(4500)
    page.click(".kit-install-go")
    page.wait_for_timeout(300)
    check("Install: prompt() once", js("window.prompted") == 1)
    check("Install: bar gone, offer let go", not js(SHOWN) and js("kitInstall.state().offer") is False)
    page.click("nav.kit-tabs [data-menu-btn]")
    page.wait_for_timeout(400)
    page.click("#menuPanel a[href='/prev/settings/']")
    page.wait_for_url("**/settings/")
    page.wait_for_timeout(500)
    check("Settings after Install: no second Add button", js("document.querySelectorAll('.kit-set-ibtn').length") == 0)

    # the offer caught on another page reaches the Settings row (a boosted tap)
    js("localStorage.removeItem('pypenInstallNudge')")  # the accepted prompt above: gone for good
    load(page, "/prev/pens/")
    js(OFFER, "dismissed")
    page.wait_for_timeout(4500)
    check("bar shows before Settings", js(SHOWN))
    page.click("nav.kit-tabs [data-menu-btn]")
    page.wait_for_timeout(400)
    page.click("#menuPanel a[href='/prev/settings/']")
    page.wait_for_url("**/settings/")
    page.wait_for_timeout(500)
    check("Settings: the row offers Add", js("document.querySelectorAll('.kit-set-ibtn').length") == 1)
    js("window.prompted = 0")
    page.click(".kit-set-ibtn")
    page.wait_for_timeout(300)
    check("Settings Add: prompt() once, bar gone", js("window.prompted") == 1 and not js(SHOWN))
    check("Settings Add: the bar let go of it", js("kitInstall.state().offer") is False)

    # the demo for screenshots
    js("localStorage.removeItem('pypenInstallNudge')")
    load(page, "/prev/dashboard/?installdemo=1")
    page.wait_for_timeout(800)
    check("?installdemo=1 shows it", js(SHOWN))
    shot(page, "installbar-demo.png")


def iphone(b):
    ctx = b.new_context(
        viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True, user_agent=IPHONE, service_workers="block"
    )
    return ctx


def main():
    with tempfile.TemporaryDirectory() as tmp:
        proc, sess = lp.start(tmp)
        try:
            with sync_playwright() as p:
                b = p.chromium.launch()
                ctx = b.new_context(
                    viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True, service_workers="block"
                )
                ctx.add_cookies([{"name": "sessionid", "value": sess, "url": BASE}])
                page = ctx.new_page()
                errs = []
                page.on("pageerror", lambda e: errs.append(str(e)))
                run(ctx, page)
                ctx.close()

                ctx = iphone(b)
                ctx.add_cookies([{"name": "sessionid", "value": sess, "url": BASE}])
                page = ctx.new_page()
                page.on("pageerror", lambda e: errs.append(str(e)))
                load(page, "/prev/dashboard/")
                page.wait_for_timeout(4500)
                check("iPhone: the bar with the Share words", page.evaluate(SHOWN))
                check("iPhone: no Install button", page.evaluate("document.querySelector('.kit-install-go').hidden"))
                check("iPhone: Share text", "Share" in page.evaluate("document.querySelector('#installbar small').textContent"))
                shot(page, "installbar-iphone.png")
                ctx.close()

                # a stranger: the front page has no bar
                ctx = b.new_context(viewport={"width": 390, "height": 844}, user_agent=IPHONE, service_workers="block")
                page = ctx.new_page()
                load(page, "/")
                page.wait_for_timeout(4500)
                check("stranger: no bar", page.evaluate("!document.getElementById('installbar')"))
                ctx.close()

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
