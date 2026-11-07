"""The new version under /next/ (PYPEN-11): same views, its own pages. tests_doors
walks its routes for the door; this holds what is particular to it."""

import json
import re
from datetime import date, timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from dpypen.items import skin
from dpypen.items.models import Brand, Ink, Nib, Pen, PenPhoto, Rotation, Usage
from dpypen.items.nextui import color, stats
from dpypen.items.tests import PLAIN_STATIC

HERE = Path(__file__).resolve().parent
PAGES = (
    "/next/", "/next/pens/", "/next/pens/?view=grid", "/next/inks/", "/next/inks/?view=list", "/next/usages/",
    "/next/pick/", "/next/search/", "/next/search/?q=pel", "/next/settings/", "/next/stats/", "/next/stats/inkings/",
    "/next/stats/collection/", "/next/stats/cupboard/", "/next/stats/rotation/", "/next/stats/timeline/",
    "/next/stats/timeline/?rot=p1", "/next/stats/calendar/", "/next/stats/pairs/", "/next/stats/records/",
    "/next/pens/add/", "/next/inks/add/", "/next/usages/add/", "/next/pens/needs-photos/", "/next/import/",
    "/next/supen/", "/next/supen/?rot=p1&sort=fills", "/next/supen/?rot=out", "/next/suink/", "/next/suink/?rot=easy&sort=name",
)
# The old pages' addresses, which a page of the new version must not lead to.
OLD_LINK = re.compile(r'(?:href|action)="(/(?:pens|inks|usages|dashboard|history|records|search|settings|import|pick)/[^"]*)"')


class Seeded(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("owner", password="x")
        brand = Brand.objects.create(name="Pelikan", nationality="DE")
        cls.rot = Rotation.objects.create(priority=1, how_often=30, whos="Tomek", in_use=True)
        today = date.today()
        cls.pen = Pen.objects.create(obtained=date(2020, 1, 1), brand=brand, model="M800", filling="Piston", age="Modern",
                                     obtained_from="shop", out=False, price=1000, rotation=cls.rot)
        cls.due = Pen.objects.create(obtained=date(2020, 1, 1), brand=brand, model="M200", filling="c/c", age="Modern",
                                     obtained_from="shop", out=False, price=100, rotation=cls.rot)
        cls.ink = Ink.objects.create(brand=brand, name="4001 Blue", color="Blue", obtained_from="shop", how="Bought", volume=50,
                                     rotation=cls.rot, used_up=False, sampled_hex=["#112266", "#2244aa"])
        cls.red = Ink.objects.create(brand=brand, name="Ruby", color="Red", obtained_from="shop", how="Bought", volume=50,
                                     rotation=cls.rot, used_up=False)
        cls.nib = Nib.objects.create(width="F", cut="round", material="14k")
        cls.old = Usage.objects.create(pen=cls.due, nib=cls.nib, ink=cls.red, begin=date(2024, 1, 10), end=date(2024, 2, 10))
        cls.now = Usage.objects.create(pen=cls.pen, nib=cls.nib, ink=cls.ink, begin=today - timedelta(days=5))
        PenPhoto.objects.bulk_create([PenPhoto(pen=cls.pen, image="pen_photos/a.jpg")])


@override_settings(STORAGES=PLAIN_STATIC)
class Pages(Seeded):
    def setUp(self):
        self.client.force_login(self.owner)

    def test_every_page_answers_and_stays_in_the_new_version(self):
        for url in (*PAGES, f"/next/pens/{self.pen.pk}/", f"/next/inks/{self.ink.pk}/", f"/next/pens/{self.pen.pk}/edit/",
                    f"/next/inks/{self.ink.pk}/edit/", f"/next/usages/{self.now.pk}/edit/"):
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 200)
                html = r.content.decode()
                self.assertIn('next/next.css', html)
                self.assertEqual(OLD_LINK.findall(html), [])

    def test_pages_with_nothing_in_the_database(self):
        for model in (Usage, Pen, Ink):
            model.objects.all().delete()
        for url in PAGES:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_a_form_saved_here_lands_here(self):
        r = self.client.post("/next/usages/add/", {"pen": self.due.pk, "nib": self.nib.pk, "ink": self.red.pk, "begin": "2026-01-01"})
        self.assertRedirects(r, f"/next/pens/{self.due.pk}/", fetch_redirect_response=False)
        r = self.client.post(f"/next/usages/{self.now.pk}/end/")
        self.assertRedirects(r, "/next/usages/", fetch_redirect_response=False)
        self.now.refresh_from_db()
        self.assertEqual(self.now.end, date.today())

    def test_an_undo_after_a_change_here_comes_back_here(self):
        self.client.post(f"/next/usages/{self.now.pk}/end/")
        html = self.client.get("/next/usages/").content.decode()
        token = re.search(r'action="/undo/([^/]+)/"', html).group(1)
        r = self.client.post(f"/undo/{token}/", {"next": "/next/usages/"})
        self.assertRedirects(r, "/next/usages/", fetch_redirect_response=False)
        self.now.refresh_from_db()
        self.assertIsNone(self.now.end)

    def test_the_old_address_of_the_picker_lands_on_the_picker(self):
        r = self.client.get(f"/next/?pen={self.due.pk}&shuffle=2")
        self.assertEqual(r.status_code, 307)
        self.assertEqual(r["Location"], f"/next/pick/?pen={self.due.pk}&shuffle=2")
        self.assertEqual(self.client.get("/pick/").status_code, 200)

    def test_a_404_here_keeps_this_look(self):
        with override_settings(DEBUG=False):
            html = self.client.get("/next/no-such-page/", headers={"Accept": "text/html"}).content.decode()
        self.assertIn("next/next.css", html)

    def test_the_tab_bar_lights_the_place_of_each_page(self):
        """The kit's tab bar (KIT-TABS): one tab marked, sub-pages too, and a page
        behind More (Inkings, the picker, search, settings) lights More."""
        more = 'data-phone data-menu-btn'
        cases = {"/next/": "Desk", "/next/pens/": "Pens", "/next/pens/needs-photos/": "Pens", "/next/inks/": "Inks",
                 "/next/stats/": "Stats", "/next/stats/records/": "Stats", "/next/stats/pairs/": "Stats",
                 "/next/usages/": more, "/next/pick/": more, "/next/search/?q=blue": more, "/next/settings/": more}
        for url, tab in cases.items():
            html = self.client.get(url).content.decode()
            html = html[html.index('<nav class="kit-tabs"') : html.index("</nav>", html.index('<nav class="kit-tabs"'))]
            with self.subTest(url=url):
                self.assertEqual(html.count('aria-current="page"'), 1)
                lit = html[: html.index('aria-current="page"')]
                lit = lit[lit.rindex('class="kit-tab"') :] + html[html.index('aria-current="page"') :][:400]
                self.assertIn(tab if tab == more else "<span>%s</span>" % tab, lit)

    def test_list_rows_cost_no_query_per_row(self):
        with self.assertNumQueries(self._queries_for("/next/pens/")):
            self.client.get("/next/pens/")
        for i in range(20):
            Pen.objects.create(obtained=date(2020, 1, 1), brand=self.pen.brand, model=f"Extra {i}", filling="Piston", age="Modern",
                               obtained_from="shop", out=False, price=10, rotation=self.rot)
        self.client.get("/next/pens/")
        with self.assertNumQueries(self._queries_for("/next/pens/")):
            self.client.get("/next/pens/")

    def _queries_for(self, url):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            self.client.get(url)
        return len(ctx)


@override_settings(STORAGES=PLAIN_STATIC)
class WhichOpensFirst(Seeded):
    def setUp(self):
        self.client.force_login(self.owner)

    def test_the_old_desk_is_the_default(self):
        self.assertEqual(self.client.get("/dashboard/").status_code, 200)

    def test_choosing_it_redirects_the_old_desk_and_going_back_undoes_it(self):
        self.client.post("/next/prefer/", {"first": "next"})
        r = self.client.get("/dashboard/")
        self.assertEqual(r.status_code, 307)
        self.assertEqual(r["Location"], "/next/")
        # A soft navigation keeps the page it is in.
        self.assertEqual(self.client.get("/dashboard/", headers={"HX-Request": "true"}).status_code, 200)
        r = self.client.post("/next/prefer/", {"first": "old", "leave": "1"})
        self.assertEqual(r["Location"], "/dashboard/")
        self.assertEqual(self.client.get("/dashboard/").status_code, 200)

    def test_the_old_version_leads_here(self):
        html = self.client.get("/dashboard/").content.decode()
        self.assertIn('href="/next/" class="menu-link" hx-boost="false"', html)
        self.assertIn('href="/next/"', self.client.get("/settings/").content.decode())

    def test_the_prefer_door_is_post_only(self):
        self.assertEqual(self.client.get("/next/prefer/").status_code, 405)


class Numbers(Seeded):
    def test_the_river_counts_a_fill_in_each_month_it_runs(self):
        rows = stats.load()
        river = stats.river(rows, date.today())
        names = {s["name"] for s in river["shapes"]}
        self.assertEqual(names, {"Blue", "Red"})
        months = river["data"]["months"]
        jan = next(m for m in months if m[0] == "Jan 2024")
        # 10-31 Jan is 22 of 31 days of one pen.
        self.assertAlmostEqual(jan[1], 0.7, places=1)
        self.assertEqual(river["data"]["colors"][jan[2][0][0]], "Red")

    def test_first_pairs_counts_a_repeat_once(self):
        Usage.objects.create(pen=self.due, nib=self.nib, ink=self.red, begin=date(2024, 3, 1), end=date(2024, 3, 2))
        rows = stats.load()
        self.assertEqual(len(stats.first_pairs(rows)), 2)

    def test_same_period_stops_at_todays_date(self):
        today = date(2026, 3, 1)
        pens, inks = [], []
        rows = stats.load()
        got = stats._same_period(rows, 2024, today, pens, inks, stats.first_pairs(rows))
        self.assertEqual(got["inkings"], 1)
        got = stats._same_period(rows, 2024, date(2026, 1, 5), pens, inks, stats.first_pairs(rows))
        self.assertEqual(got["inkings"], 0)

    def test_a_chart_link_goes_to_the_twin(self):
        self.assertEqual(stats.rebase({"links": "See them|/usages/?began=2024", "url": "/usages/?color=Blue"}),
                         {"links": "See them|/next/usages/?began=2024", "url": "/next/usages/?color=Blue"})

    def test_rotation_splits_the_pens(self):
        data = stats.rotation()
        g = data["groups"][0]
        self.assertEqual(g["n"], 2)
        self.assertEqual({s["key"]: s["n"] for s in g["segments"]}, {"inked": 1, "over": 1})
        self.assertEqual(g["on_time"], 50)

    def test_a_chinese_brand_is_not_swiss(self):
        self.assertEqual(stats._country(Brand(name="Jinhao", nationality="CH")), "China")
        self.assertEqual(stats._country(Brand(name="Caran d'Ache", nationality="CH")), "Switzerland")


class Accent(TestCase):
    def test_any_ink_is_readable_as_the_accent_in_both_themes(self):
        for hex_ in ("#d4b12c", "#1b2a4a", "#34a0a4", "#d87aa5", "#6f1d2c", "#ffffff", "#000000", None):
            a = color.accent(hex_)
            for paper in (color.PAGE_LIGHT, color.PANEL_LIGHT):
                self.assertGreaterEqual(color.contrast(a["light"], paper), 4.5, hex_)
            for paper in (color.PAGE_DARK, color.PANEL_DARK):
                self.assertGreaterEqual(color.contrast(a["dark"], paper), 4.5, hex_)
            self.assertGreaterEqual(color.contrast(a["light"], a["on_light"]), 4.5, hex_)
            self.assertGreaterEqual(color.contrast(a["dark"], a["on_dark"]), 4.5, hex_)

    def test_a_black_has_no_colour_to_lend(self):
        self.assertFalse(color.chromatic("#1f1d1a"))
        self.assertTrue(color.chromatic("#2a5caa"))


class Skin(TestCase):
    def test_a_redirect_to_a_page_without_a_twin_stays(self):
        self.assertEqual(skin.to_next("/accounts/google/login/?next=/next/"), "/accounts/google/login/?next=/next/")
        self.assertEqual(skin.to_next("/pens/5/"), "/next/pens/5/")
        self.assertEqual(skin.to_next("/next/pens/5/"), "/next/pens/5/")

    def test_the_river_data_cannot_close_its_script_tag(self):
        from dpypen.items.templatetags.items_extras import json_script_safe

        text = json_script_safe({"a": "</script>&"})
        self.assertNotIn("</script>", text)
        self.assertEqual(json.loads(text), {"a": "</script>&"})
