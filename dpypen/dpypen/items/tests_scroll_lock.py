"""An overlay freezes the page under it (~/apps/kit/README.md, "Dialogs & sheets").

2026-09-27: on a phone the page ran on underneath the keyboard layer's
palette and ? sheet. The lock is one class on <html>, set by one watcher in
_shell.html, with the CSS in app.css. The browser half of the check is
tools/scroll_lock_probe.py (run it against a copy of the database).
"""

from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from dpypen.items.tests import PLAIN_STATIC

APP_CSS = Path(__file__).resolve().parent / "static" / "items" / "css" / "app.css"


@override_settings(STORAGES=PLAIN_STATIC)
class ScrollLock(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("owner", password="x")

    def setUp(self):
        self.client.force_login(self.user)

    def test_every_shell_page_carries_the_watcher(self):
        for url in ("/pens/", "/inks/", "/history/"):
            html = self.client.get(url).content.decode()
            self.assertIn('id="kpal"', html, url)
            self.assertIn('var OPEN = "#kpal.on,#khelp.on";', html, url)
            self.assertIn('root.classList.toggle("scroll-lock"', html, url)
            self.assertIn("items/css/app.css", html, url)

    def test_app_css_holds_the_lock(self):
        css = APP_CSS.read_text()
        self.assertIn("html.scroll-lock, html.scroll-lock body { overflow: hidden; }", css)
        self.assertIn("html:has(dialog[open]:modal) { overflow: hidden; }", css)
        self.assertIn("#kpal .kp-list, #khelp .kh-card { overscroll-behavior: contain; }", css)
