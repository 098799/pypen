"""Overlays go through the kit's layer (_layer.js, KIT-LAYER; kit README §4
"Dialogs & sheets"): the menu, a detail page's "⋯" panel and the gantt popup.

Headless Chromium at 390×844 against a throwaway copy of the local database
(a temp dir, a spare port, DEBUG on, a session made in the copy): never the
live data on bae, never the local db.sqlite3 itself.

    python3 tools/layer_probe.py        # playwright on the system python
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "dpypen"
PY = ROOT / ".devvenv" / "bin" / "python"
PORT = int(os.environ.get("PROBE_PORT", "18491"))
BASE = f"http://127.0.0.1:{PORT}"
failures = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def start(tmp):
    try:
        urllib.request.urlopen(BASE + "/", timeout=1)
        sys.exit(f"port {PORT} is taken; set PROBE_PORT")
    except urllib.error.HTTPError:
        sys.exit(f"port {PORT} is taken; set PROBE_PORT")
    except OSError:
        pass
    db = Path(tmp) / "db.sqlite3"
    shutil.copy(APP / "db.sqlite3", db)
    (Path(tmp) / "probe_settings.py").write_text(
        "from dpypen.settings import *  # noqa\n"
        f"DATABASES['default']['NAME'] = {str(db)!r}\n"
        f"MEDIA_ROOT = {str(Path(tmp) / 'media')!r}\n")
    env = dict(os.environ, DJANGO_SETTINGS_MODULE="probe_settings", DEBUG="True",
               SECRET_KEY="probe-not-a-secret", PYTHONPATH=f"{tmp}:{APP}")
    sess = subprocess.run([str(PY), "-c", (
        "import django; django.setup()\n"
        "from django.contrib.auth import get_user_model\n"
        "from django.contrib.sessions.backends.db import SessionStore\n"
        "from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY\n"
        "U = get_user_model(); u = U.objects.filter(is_superuser=True).first() or U.objects.create_user('probe')\n"
        "s = SessionStore(); s[SESSION_KEY] = str(u.pk)\n"
        "s[BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'\n"
        "s[HASH_SESSION_KEY] = u.get_session_auth_hash(); s.create(); print(s.session_key)\n")],
        cwd=APP, env=env, capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1]
    proc = subprocess.Popen([str(PY), "manage.py", "runserver", "--noreload", f"127.0.0.1:{PORT}"],
                            cwd=APP, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            urllib.request.urlopen(BASE + "/healthz", timeout=1)
            break
        except urllib.error.HTTPError:
            break
        except OSError:
            time.sleep(0.5)
    return proc, sess


def lock(page):
    return page.evaluate("document.documentElement.classList.contains('scroll-lock')")


def run(page):
    # The menu, opened from the phone tab bar's "More".
    page.goto(BASE + "/pens/")
    page.wait_for_load_state("networkidle")
    url = page.url
    check("kitLayer loaded", page.evaluate("kitLayer.version") == "v1 2026-10-30")
    check("closed menu is out of the tab order",
          page.evaluate("getComputedStyle(document.getElementById('menuPanel')).visibility") == "hidden")
    more = page.locator(".tabbar [data-menu-btn]")
    more.click()
    page.wait_for_timeout(300)
    check("menu: open", page.evaluate("document.getElementById('menuPanel').classList.contains('open')"))
    check("menu: a history entry", (page.evaluate("history.state") or {}).get("kitLayer") == 1)
    check("menu: page not locked (anchored)", not lock(page))
    page.go_back()
    page.wait_for_timeout(400)
    check("menu: Back closes it", not page.evaluate("document.getElementById('menuPanel').classList.contains('open')"))
    check("menu: Back stays on the page", page.url == url)
    check("menu: focus back on More", page.evaluate("document.activeElement.matches('.tabbar [data-menu-btn]')"))
    # Esc
    more.click(); page.wait_for_timeout(300)
    page.keyboard.press("Escape"); page.wait_for_timeout(400)
    check("menu: Esc closes it", not page.evaluate("document.getElementById('menuPanel').classList.contains('open')"))
    check("menu: Esc leaves no entry", not (page.evaluate("history.state") or {}).get("kitLayer"))
    # A link in the menu: the menu goes, then htmx navigates; Back lands on the page, menu shut.
    more.click(); page.wait_for_timeout(300)
    link = page.locator("#menuPanel a[href='/inks/']").first
    if link.count() == 0:
        link = page.locator("#menuPanel a[href^='/']:not([href='/pens/'])").first
    target = link.get_attribute("href")
    link.click()
    page.wait_for_url("**" + target.split("?")[0] + "*", timeout=8000)
    page.wait_for_timeout(600)
    check("menu link: followed", page.url.startswith(BASE + target.split("?")[0]))
    check("menu link: menu gone", not page.evaluate("document.getElementById('menuPanel').classList.contains('open')"))
    page.go_back()
    page.wait_for_timeout(900)
    check("menu link: Back lands on the list", page.url == url)
    check("menu link: ... with the menu shut",
          not page.evaluate("document.getElementById('menuPanel').classList.contains('open')"))
    # After htmx's Back (the body rewritten from its snapshot) the menu still works.
    page.locator(".tabbar [data-menu-btn]").click(); page.wait_for_timeout(300)
    check("after htmx Back: menu opens", page.evaluate("document.getElementById('menuPanel').classList.contains('open')"))
    page.go_back(); page.wait_for_timeout(400)
    check("after htmx Back: Back closes it",
          not page.evaluate("document.getElementById('menuPanel').classList.contains('open')") and page.url == url)
    # Reload with the menu open: one Back then leaves the page.
    page.goto(BASE + "/inks/"); page.wait_for_load_state("networkidle")
    page.goto(BASE + "/pens/"); page.wait_for_load_state("networkidle")
    page.locator(".tabbar [data-menu-btn]").click(); page.wait_for_timeout(300)
    page.reload(); page.wait_for_load_state("networkidle"); page.wait_for_timeout(300)
    check("reload: lands on the page", not (page.evaluate("history.state") or {}).get("kitLayer"))
    page.go_back(); page.wait_for_timeout(800)
    check("reload: one Back leaves the page", page.url.startswith(BASE + "/inks/"))

    # The "⋯" panel on a pen.
    page.goto(BASE + "/pens/"); page.wait_for_load_state("networkidle")
    href = page.locator("#main a[href^='/pens/']").evaluate_all(
        "as => as.map(a => a.getAttribute('href')).find(h => /^\\/pens\\/\\d+\\/$/.test(h))")
    page.goto(BASE + href); page.wait_for_load_state("networkidle")
    purl = page.url
    btn = page.locator("[data-overflow-btn]")
    btn.click(); page.wait_for_timeout(300)
    check("⋯: open", page.evaluate("!!document.querySelector('.overflow-panel.open')"))
    check("⋯: aria-expanded", btn.get_attribute("aria-expanded") == "true")
    page.go_back(); page.wait_for_timeout(400)
    check("⋯: Back closes it", not page.evaluate("!!document.querySelector('.overflow-panel.open')"))
    check("⋯: Back stays on the pen", page.url == purl)
    btn.click(); page.wait_for_timeout(300)
    page.mouse.click(30, 700); page.wait_for_timeout(400)
    check("⋯: a tap outside closes it", not page.evaluate("!!document.querySelector('.overflow-panel.open')"))
    check("⋯: ... and gives the entry back", not (page.evaluate("history.state") or {}).get("kitLayer"))

    # The gantt popup.
    page.goto(BASE + "/history/gantt/"); page.wait_for_load_state("networkidle")
    gurl = page.url
    bar = page.locator(".gantt-bar").first
    if bar.count():
        bar.scroll_into_view_if_needed()
        bar.click(force=True); page.wait_for_timeout(300)
        check("gantt: open", page.evaluate("document.getElementById('ganttPopup').classList.contains('open')"))
        page.go_back(); page.wait_for_timeout(400)
        check("gantt: Back closes it",
              not page.evaluate("document.getElementById('ganttPopup').classList.contains('open')"))
        check("gantt: Back stays on the page", page.url == gurl)
    else:
        check("gantt: a bar to tap", False)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        proc, sess = start(tmp)
        try:
            with sync_playwright() as p:
                b = p.chromium.launch()
                ctx = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True,
                                    service_workers="block")
                ctx.add_cookies([{"name": "sessionid", "value": sess, "url": BASE}])
                page = ctx.new_page()
                errs = []
                page.on("pageerror", lambda e: errs.append(str(e)))
                run(page)
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
