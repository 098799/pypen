"""The kit pieces PYPEN-2 added, in a real browser: pull to refresh, the
new-version toast, What's new, the error pages (also through an hx-boost
swap), and the scroll lock under the What's new log.

Headless Chromium at 390×844 (touch) against a throwaway copy of the local
database on a spare port, with DEBUG off (Django's debug 404 would hide the
app's own) and plain static files: never the live data on bae, never the local
db.sqlite3 itself. Shares layer_probe's start-up.

    python3 tools/kit_probe.py                     # playwright on the system python
    SHOTS=/some/dir python3 tools/kit_probe.py     # also keep screenshots
"""

import os
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layer_probe as lp  # noqa: E402

lp.PORT = int(os.environ.get("PROBE_PORT", "18493"))
lp.BASE = BASE = f"http://127.0.0.1:{lp.PORT}"
check, failures = lp.check, lp.failures
SHOTS = os.environ.get("SHOTS")

# DEBUG off for the app's own error pages; then runserver serves the static
# files only with --insecure, and the hashed storage needs a collectstatic.
_write = Path.write_text


def _settings(self, text, *a, **k):
    if self.name == "probe_settings.py":
        text += (
            "DEBUG = False\nALLOWED_HOSTS = ['127.0.0.1']\n"
            "SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = False\n"
            "STORAGES = {'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},"
            " 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}}\n"
        )
    return _write(self, text, *a, **k)


def shot(page, name):
    if SHOTS:
        page.screenshot(path=os.path.join(SHOTS, name))


def drag(page, cdp, x, y, dy, steps=8):
    send = lambda kind, pts: cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": pts})  # noqa: E731
    send("touchStart", [{"x": x, "y": y}])
    for i in range(1, steps + 1):
        send("touchMove", [{"x": x, "y": y + dy * i / steps}])
        page.wait_for_timeout(16)
    send("touchEnd", [])


def run(page, cdp):
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    # Pull to refresh: a long pull from the top loads the page again.
    page.goto(BASE + "/pens/")
    page.wait_for_load_state("networkidle")
    check("pull: active on a touch screen", page.evaluate("kitPull.active") is True)
    page.evaluate("window.stamp = 1")
    drag(page, cdp, 195, 300, 260)
    try:
        page.wait_for_function("window.stamp === undefined", timeout=4000)
        check("pull: a long pull reloads", True)
    except Exception:
        check("pull: a long pull reloads", False)
    page.wait_for_load_state("networkidle")

    # New version: the page's build against /api/version.
    check("update: the page knows its build", page.evaluate("fetch('/api/version').then(r => r.json()).then(j => j.build === KITUPDATE.build.id)"))
    page.evaluate("KITUPDATE.build.id = 'old-build'; kitUpdate.check()")
    page.wait_for_timeout(800)
    check(
        "update: an old page is offered the new version",
        page.evaluate("document.getElementById('kit-update') && document.getElementById('kit-update').classList.contains('on')"),
    )
    check("update: words", "New version ready" in (page.text_content("#kit-update") or ""))
    box = page.evaluate(
        "(() => { const r = document.getElementById('kit-update').getBoundingClientRect();"
        " const t = document.querySelector('nav.kit-tabs').getBoundingClientRect(); return [r.bottom, t.top]; })()"
    )
    check("update: above the tab bar", box[0] <= box[1])
    shot(page, "update-toast.png")
    page.reload()
    page.wait_for_load_state("networkidle")

    # What's new: from Settings; a modal sheet; Back closes it and stays.
    page.goto(BASE + "/settings/")
    page.wait_for_load_state("networkidle")
    url = page.url
    page.locator("button[data-whatsnew-open]").click()
    page.wait_for_timeout(600)
    check("whatsnew: the log opens", page.evaluate("!!document.querySelector('dialog#kit-wn[open]')"))
    # What's new locks with its own class (kit-wn-lock), not html.scroll-lock:
    # the page's overflow is what counts (until PYPEN-8 a watcher in
    # _shell.html also set scroll-lock under any modal dialog).
    check("whatsnew: the page under it is locked",
          page.evaluate("getComputedStyle(document.documentElement).overflow === 'hidden'"
                        " && getComputedStyle(document.body).overflow === 'hidden'"))
    check(
        "whatsnew: it lists the entries",
        page.evaluate("document.querySelectorAll('#kit-wn [data-id], #kit-wn .kit-wn-item, #kit-wn article').length") >= 1,
    )
    shot(page, "whatsnew-log.png")
    page.go_back()
    page.wait_for_timeout(700)
    check("whatsnew: Back closes it", not page.evaluate("!!document.querySelector('dialog#kit-wn[open]')"))
    check("whatsnew: ... and stays on Settings", page.url == url)
    check("whatsnew: ... and unlocks the page", not page.evaluate("document.documentElement.classList.contains('scroll-lock')"))

    # The palette's entry opens it too.
    page.evaluate("window.__go('#whatsnew')")
    page.wait_for_timeout(600)
    check("whatsnew: the palette entry opens it", page.evaluate("!!document.querySelector('dialog#kit-wn[open]')"))
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)

    # Error pages: a load, and a boosted link (htmx swaps no 4xx by itself).
    r = page.goto(BASE + "/pens/987654321/")
    check("404: status", r.status == 404)
    check("404: in the app's chrome", page.locator("nav.kit-tabs").count() == 1 and "Not here" in page.content())
    shot(page, "error-404.png")
    page.goto(BASE + "/pens/")
    page.wait_for_load_state("networkidle")
    page.evaluate("""(() => { const a = document.createElement('a'); a.href = '/pens/987654321/';
                     a.id = 'deadlink'; a.textContent = 'dead'; document.getElementById('main').prepend(a);
                     htmx.process(a); })()""")
    page.click("#deadlink")
    page.wait_for_timeout(1200)
    check("404 boosted: the page is swapped in", "Not here" in (page.text_content("#main") or ""))
    check("404 boosted: the address is the dead one", page.url.endswith("/pens/987654321/"))
    page.locator("[data-error-back]").click()
    page.wait_for_timeout(1200)
    check("404 boosted: Back is a way on", page.url.endswith("/pens/"))

    # Nothing is wider than the phone.
    for u in ("/dashboard/", "/pens/", "/settings/"):
        page.goto(BASE + u)
        page.wait_for_load_state("networkidle")
        check(f"{u}: no sideways scroll", page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
    check("no page error", not errors)
    for e in errors:
        print("  ", e)


def main():
    Path.write_text = _settings
    with tempfile.TemporaryDirectory() as tmp:
        proc, sess = lp.start(tmp)
        Path.write_text = _write
        try:
            # runserver with DEBUG off serves /static/ only with --insecure: restart it so.
            proc.terminate()
            proc.wait(10)
            import subprocess
            import time
            import urllib.request

            env = dict(
                os.environ, DJANGO_SETTINGS_MODULE="probe_settings", DEBUG="True", SECRET_KEY="probe-not-a-secret", PYTHONPATH=f"{tmp}:{lp.APP}"
            )
            proc = subprocess.Popen(
                [str(lp.PY), "manage.py", "runserver", "--noreload", "--insecure", f"127.0.0.1:{lp.PORT}"],
                cwd=lp.APP,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            for _ in range(60):
                try:
                    urllib.request.urlopen(BASE + "/robots.txt", timeout=1)
                    break
                except OSError:
                    time.sleep(0.5)
            with sync_playwright() as p:
                b = p.chromium.launch()
                ctx = b.new_context(
                    viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True, service_workers="block"
                )
                ctx.add_cookies([{"name": "sessionid", "value": sess, "url": BASE}])
                page = ctx.new_page()
                run(page, ctx.new_cdp_session(page))
                b.close()
        finally:
            proc.terminate()
            proc.wait(10)
    print("all passed" if not failures else f"{len(failures)} FAILED: {failures}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
