"""The desk bar and the header row (PYPEN-6; kit README §4 Fleet UX "Desk"
and "Header").

One markup for both shapes: the tab bar (the kit's _tabs.html) follows #hdr,
and the kit moves it into the 52 px desk bar's slot (#desktabs) from 900 px;
below, the header is not there and the bar is fixed to the bottom.
The pill nav and the floating menu button are gone. A list screen's first row
says what it answers and how fresh, with at most two icon buttons. The
browser half (the bar's height, Filter ▾, ⌕, ⋯, a narrowed window) is
tools/desk_probe.py.
"""

import re
from datetime import date, timedelta

from django.test import Client, SimpleTestCase, override_settings

from dpypen.items.models import InviteCode, Usage
from dpypen.items.shelf import ago
from dpypen.items.tests import PLAIN_STATIC
from dpypen.items.tests_lists import Collection

NAVIGATE = {"HTTP_SEC_FETCH_MODE": "navigate", "HTTP_ACCEPT": "text/html"}


def header(html):
    return html[html.index('<header class="deskbar" id="hdr">') : html.index("</header>", html.index('id="hdr"'))]


def tabs(html):
    """The tab bar's nav (the kit's comment in _tabs.html shows the markup too)."""
    at = html.index('<nav class="kit-tabs"')
    return html[at : html.index("</nav>", at)]


def head_row(html):
    """The screen's header row, up to what follows it (the toolbar, a section)."""
    m = re.search(r'<(div|header) class="[^"]*page-head hrow[^"]*">', html)
    assert m, "no header row"
    rest = html[m.start() :]
    ends = [rest.find(t) for t in ('<div class="toolbar">', "<section", "<p class=\"page-note\"")]
    return rest[: min(e for e in ends if e > 0)]


@override_settings(STORAGES=PLAIN_STATIC)
class TheDeskBar(Collection):
    def test_one_header_with_the_tab_bar_s_slot_in_it(self):
        html = self.client.get("/pens/").content.decode()
        self.assertEqual(html.count('id="hdr"'), 1)
        hdr = header(html)
        self.assertIn('<div class="desktabs" id="desktabs"></div>', hdr)
        self.assertNotIn("kit-tabs", hdr)  # one nav, outside the header
        self.assertEqual(html.count('<nav class="kit-tabs" aria-label="Sections" data-desk-into="#desktabs">'), 1)
        # The kit's script and style come in member.js/.css (kitshell.py), not inline.
        self.assertNotIn("KIT-TABS", html)
        self.assertIn('<script src="/kit/member.js', html)
        self.assertNotIn("tabbar", html)
        self.assertIn("db-brand", hdr)
        self.assertIn('id="deskSearchBtn"', hdr)
        self.assertIn('id="deskSearch"', hdr)
        self.assertIn('id="deskFilter"', hdr)
        # the places a phone has no room for are tabs on a desk only
        for place in ("/history/", "/records/"):
            self.assertRegex(html, r'<a class="kit-tab" data-desk href="%s">' % place)
        # More is the bar's on a phone; the desk bar has ⋯
        self.assertRegex(html, r'<button type="button" class="kit-tab" data-phone data-menu-btn')
        self.assertIn('aria-label="More" aria-controls="menuPanel" data-menu-btn', hdr)
        self.assertIn("items/js/deskbar.js", html)

    def test_the_pill_nav_and_the_floating_button_are_gone(self):
        for url in ("/dashboard/", "/pens/", "/inks/", "/usages/", "/history/", "/records/", "/settings/"):
            html = self.client.get(url).content.decode()
            with self.subTest(url=url):
                self.assertNotIn("app-nav", html)
                self.assertNotIn('id="topbar"', html)
                self.assertNotIn("menu-corner", html)  # the owner has the tab bar
                self.assertNotIn('aria-labelledby="menuBtn"', html)  # it named no element

    def test_the_tab_lights_where_you_are(self):
        cases = {"/pens/": "/pens/", "/inks/": "/inks/", "/usages/": "/usages/", "/dashboard/": "/dashboard/"}
        for url, tab in cases.items():
            html = tabs(self.client.get(url).content.decode())
            with self.subTest(url=url):
                self.assertEqual(html.count('aria-current="page"'), 1)
                self.assertRegex(html, r'<a class="kit-tab" href="%s" aria-current="page">' % tab)

    def test_a_page_behind_more_lights_more(self):
        """AUDIT pass 8 T3: on a phone /history/, /records/, /pick/, search and
        settings lit no tab you could see (History and Records are desk-only
        tabs, the rest have none). They light More, where a phone has them; a
        desk-only tab is lit with it."""
        more = r'<button type="button" class="kit-tab" data-phone data-menu-btn[^>]* aria-current="page">'
        for url, desk in (("/history/", "/history/"), ("/history/inkings/", "/history/"), ("/records/", "/records/"),
                          ("/pick/", None), ("/search/?q=blue", None), ("/settings/", None)):
            html = tabs(self.client.get(url).content.decode())
            with self.subTest(url=url):
                self.assertRegex(html, more)
                if desk:
                    self.assertIn('<a class="kit-tab" data-desk href="%s" aria-current="page">' % desk, html)
                self.assertEqual(html.count('aria-current="page"'), 2 if desk else 1)

    def test_chip_rows_fold_into_filter(self):
        self.pens(2)
        self.inks(2)
        self.assertIn('data-fold="Rotation"', self.client.get("/pens/").content.decode())
        self.assertIn('data-fold="Ink filters"', self.client.get("/inks/").content.decode())
        # a filtered swap brings the row back with its mark
        part = self.client.get("/inks/?color=Blue", HTTP_HX_REQUEST="true").content.decode()
        self.assertIn('data-fold="Ink filters"', part)

    def test_the_menu_drops_what_the_bar_has_tabs_for(self):
        html = self.client.get("/pens/").content.decode()
        panel = html[html.index('id="menuPanel"') : html.index("</nav>", html.index('class="menu-nav"'))]
        for place in ("/dashboard/", "/history/", "/records/", "/usages/", "/pens/", "/inks/"):
            self.assertRegex(panel, r'href="%s" class="menu-link[^"]*" data-tab>' % place)
        for place in ("/pick/", "/import/", "/pens/needs-photos/"):
            self.assertNotRegex(panel, r'href="%s" class="menu-link[^"]*" data-tab>' % place)


@override_settings(STORAGES=PLAIN_STATIC)
class TheHeaderRow(Collection):
    def test_each_list_says_what_it_holds_and_how_fresh(self):
        self.pens(3)
        self.inks(2)
        self.usages(4)  # past, from 2024
        Usage.objects.create(pen_id=self.pens_first(), ink_id=self.inks_first(), nib=self.nib, begin=date.today() - timedelta(days=3))
        cases = {
            "/pens/": ["<b>3</b> pens", "<b>1</b> inked", "last inked 3 d ago"],
            "/inks/": ["<b>2</b> inks", "<b>1</b> in pens", "last inked 3 d ago"],
            "/usages/": ["<b>1</b> inked", "<b>4</b> past", "last 3 d ago"],
            "/dashboard/": ["last inked 3 d ago"],
        }
        for url, words in cases.items():
            row = head_row(self.client.get(url).content.decode())
            for w in words:
                with self.subTest(url=url, w=w):
                    self.assertIn(w, row)

    def pens_first(self):
        from dpypen.items.models import Pen

        return Pen.objects.first().pk

    def inks_first(self):
        from dpypen.items.models import Ink

        return Ink.objects.first().pk

    def test_at_most_two_icon_buttons(self):
        for url in ("/dashboard/", "/pens/", "/inks/", "/usages/"):
            row = head_row(self.client.get(url).content.decode())
            with self.subTest(url=url):
                self.assertLessEqual(row.count('class="icon-btn"'), 2)
                self.assertNotIn('class="toolbar"', row)

    def test_the_toolbar_lost_the_icons_the_header_took(self):
        html = self.client.get("/pens/").content.decode()
        bar = html[html.index('<div class="toolbar">') : html.index('id="rotbar"')]
        self.assertNotIn("icon-btn", bar)

    def test_the_public_cupboard_prints_no_numbers(self):
        with self.settings(PUBLIC_SHOWCASE=True):
            html = Client().get("/pub/inks/").content.decode()
        self.assertNotIn('class="hstate"', html)

    def test_no_numbers_and_no_queries_for_a_stranger(self):
        html = Client().get("/no-such-page/", **NAVIGATE).content.decode()
        self.assertNotIn('class="hstate"', html)


@override_settings(STORAGES=PLAIN_STATIC)
class AStranger(Collection):
    def test_a_stranger_has_the_corner_menu_and_the_bar_s_dots(self):
        html = Client().get("/no-such-page/", **NAVIGATE).content.decode()
        self.assertIn("menu-corner", html)
        hdr = header(html)
        self.assertIn("data-menu-btn", hdr)
        self.assertNotIn('<nav class="kit-tabs"', html)
        self.assertNotIn("deskSearchBtn", hdr)

    def test_a_guest_finds_leave_in_the_menu(self):
        invite = InviteCode.objects.create(token="guest-token", label="friend")
        guest = Client()
        guest.post(f"/i/{invite.token}/")
        html = guest.get("/pens/").content.decode()
        panel = html[html.index('id="menuPanel"') : html.index("<main")]
        self.assertIn("guest · friend", panel)
        self.assertIn('action="/i/leave/"', panel)


class Ago(SimpleTestCase):
    def test_words(self):
        today = date(2026, 11, 1)
        for days, words in [
            (0, "today"),
            (1, "yesterday"),
            (3, "3 d ago"),
            (13, "13 d ago"),
            (14, "2 wk ago"),
            (59, "8 wk ago"),
            (60, "2 mo ago"),
            (729, "24 mo ago"),
            (730, "2 yr ago"),
            (-2, "today"),
        ]:
            self.assertEqual(ago(today - timedelta(days=days), today), words, days)
        self.assertEqual(ago(None), "")
