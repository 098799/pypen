"""An overlay freezes the page under it (~/apps/kit/README.md, "Dialogs & sheets").

2026-09-27: on a phone the page ran on underneath the keyboard layer's
palette and ? sheet. The lock is one class on <html>, set by one watcher in
_shell.html, with the CSS in app.css. The browser half of the check is
tools/layer_probe.py (run it against a copy of the database).

2026-10-30: the menu, the "⋯" panels and the gantt popup are layers of the
kit's _layer.js (KIT-LAYER): Back closes them instead of leaving the page.
"""

from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from dpypen.items.tests import PLAIN_STATIC

APP_CSS = Path(__file__).resolve().parent / "static" / "items" / "css" / "app.css"
LAYER = Path(__file__).resolve().parent / "templates" / "items" / "_layer.js"
KIT_LAYER = Path("/home/tgrining/apps/kit/snippets/layer.js")


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
        self.assertIn("#kpal .kp-list, #khelp .kh-card { overscroll-behavior: contain; }", css)


@override_settings(STORAGES=PLAIN_STATIC)
class KitLayer(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("owner", password="x")

    def setUp(self):
        self.client.force_login(self.user)

    def test_the_copy_is_the_kits(self):
        if KIT_LAYER.exists():
            self.assertEqual(LAYER.read_bytes(), KIT_LAYER.read_bytes())

    def test_loaded_first_and_the_menus_use_it(self):
        for url in ("/pens/", "/history/gantt/"):
            html = self.client.get(url).content.decode()
            self.assertIn("KIT-LAYER: v1", html, url)
            head = html[: html.index("</head>")]
            self.assertIn("window.kitLayer = {", head, url)
            self.assertLess(html.index("window.kitLayer = {"), html.index("htmx-2.0.4"), url)
            self.assertIn('name: "menu", lock: false, focus: false', html, url)
            self.assertIn('name: "overflow", lock: false, focus: false', html, url)
            # no own overlay history or Escape left for the menus
            self.assertNotIn('window.addEventListener("popstate", closeMenu)', html, url)
            self.assertNotIn('if (e.key === "Escape") closeMenu()', html, url)
        gantt = self.client.get("/history/gantt/").content.decode()
        self.assertIn('name: "gantt", lock: false, focus: false', gantt)
        self.assertNotIn('if (e.key === "Escape") closePopup()', gantt)

    def test_a_closed_menu_is_out_of_the_tab_order(self):
        css = APP_CSS.read_text()
        self.assertIn(".menu-panel.open { opacity: 1; transform: translateY(0); pointer-events: auto; visibility: visible;", css)
