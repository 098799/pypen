"""An overlay freezes the page under it (~/apps/kit/README.md, "Dialogs & sheets").

2026-09-27: on a phone the page ran on underneath the keyboard layer's
palette and ? sheet. The lock is one class on <html>, set by one watcher in
_shell.html, with the CSS in app.css. The browser half of the check is
tools/layer_probe.py (run it against a copy of the database).

2026-10-30: the menu, the "⋯" panels and the gantt popup are layers of the
kit's _layer.js (KIT-LAYER): Back closes them instead of leaving the page.

2026-11-01 (PYPEN-8): the keyboard layer's palette and ? sheet are kit layers
too (KEYS-LAYER v1.3), so the kit sets the lock for them and the watcher in
_shell.html is gone. The browser half is tools/layer_probe.py.
"""

import re
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from dpypen.items.tests import PLAIN_STATIC

APP_CSS = Path(__file__).resolve().parent / "static" / "items" / "css" / "app.css"
LAYER = Path(__file__).resolve().parent / "templates" / "items" / "_layer.js"
KIT_LAYER = Path("/home/tgrining/apps/kit/snippets/layer.js")
KEYS = Path(__file__).resolve().parent / "templates" / "items" / "_keys.html"
KIT_KEYS = Path("/home/tgrining/apps/kit/snippets/keys.html")


@override_settings(STORAGES=PLAIN_STATIC)
class ScrollLock(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("owner", password="x")

    def setUp(self):
        self.client.force_login(self.user)

    def test_the_kit_locks_for_the_palette_and_the_sheet(self):
        for url in ("/pens/", "/inks/", "/history/"):
            html = self.client.get(url).content.decode()
            self.assertIn('id="kpal"', html, url)
            # KEYS-LAYER v1.3 opens both through kitLayer, which sets the lock
            self.assertIn("window.__keysLayer = 'v1.3", html, url)
            self.assertIn("L.open(pal, {name: 'palette', show: palShow, close: palHide, focus: palIn})", html, url)
            self.assertIn("L.open(help, {name: 'keys', show: helpShow, close: helpHide})", html, url)
            # so pypen keeps no watcher of its own (PYPEN-8)
            self.assertNotIn('var OPEN = "#kpal.on,#khelp.on"', html, url)
            self.assertNotIn('root.classList.toggle("scroll-lock"', html, url)
            self.assertIn("items/css/app.css", html, url)

    def test_the_public_page_names_no_path_of_the_box(self):
        html = self.client.get("/pens/").content.decode()
        # the ? sheet showed "The whole dialect: ~/apps/kit/KEYS.md" (PYPEN-8)
        self.assertNotIn("The whole dialect", html)
        self.assertIn("placeholder: 'Jump to a pen, an ink, anywhere", html)

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
            # shell.js starts with the layer and loads blocking at the top of
            # <body>: it runs before htmx, which is `defer` (kitshell.py).
            from dpypen.items import kitshell
            self.assertTrue(kitshell.KIT.files["shell.js"][0].startswith(b"/*! KIT-LAYER: v1"))
            self.assertIn('<script src="/kit/shell.js', html, url)
            self.assertIn("htmx-2.0.4.min.js\" defer>", html, url)
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


def shared(text):
    """The keyboard layer's shared code: everything but the header, pypen's
    token block, CONFIG and SHEET (kit README §6: only those may differ)."""
    body = text[text.index('<div id="khud"'):]
    head = text[text.index("#khud{position"):text.index('<div id="khud"')]
    config_end = body.index("  // ——— mode:")
    sheet = body.index("  var SHEET = [")
    after = body.index("  // The sheet is searchable")
    return head, body[:body.index("  // ——— CONFIG")], body[config_end:sheet], body[after:]


class KeysCopy(TestCase):
    def test_the_shared_code_is_the_kits(self):
        if not KIT_KEYS.exists():
            self.skipTest("no kit on this box")
        mine, kit = shared(KEYS.read_text()), shared(KIT_KEYS.read_text())
        for i, (a, b) in enumerate(zip(mine, kit)):
            self.assertEqual(a, b, f"part {i} of _keys.html differs from the kit's keys.html")

    def test_the_stamp_is_the_kits(self):
        if not KIT_KEYS.exists():
            self.skipTest("no kit on this box")
        stamp = re.compile(r"KEYS-LAYER: (v\d+\.\d+ \d{4}-\d\d-\d\d)")
        self.assertEqual(stamp.search(KEYS.read_text()).group(1), stamp.search(KIT_KEYS.read_text()).group(1))
