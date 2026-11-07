"""The new version (PYPEN-11), on the main addresses since Nov 2026 (the old one
is /prev/): same views, its own pages. tests_doors walks its routes for the
door; this holds what is particular to it."""

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
    "/dashboard/", "/pens/", "/pens/?view=grid", "/inks/", "/inks/?view=list", "/usages/",
    "/pick/", "/search/", "/search/?q=pel", "/settings/", "/stats/", "/stats/inkings/",
    "/stats/collection/", "/stats/cupboard/", "/stats/rotation/", "/stats/timeline/",
    "/stats/timeline/?rot=p1", "/stats/calendar/", "/stats/pairs/", "/stats/records/",
    "/pens/add/", "/inks/add/", "/usages/add/", "/pens/needs-photos/", "/import/",
    "/supen/", "/supen/?rot=p1&sort=fills", "/supen/?rot=out", "/suink/", "/suink/?rot=easy&sort=name",
)
# The old pages' addresses, which a page of the new version must not lead to.
OLD_LINK = re.compile(r'(?:href|action)="(/prev/[^"]*)"')


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
        for url in (*PAGES, f"/pens/{self.pen.pk}/", f"/inks/{self.ink.pk}/", f"/pens/{self.pen.pk}/edit/",
                    f"/inks/{self.ink.pk}/edit/", f"/usages/{self.now.pk}/edit/"):
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 200)
                html = r.content.decode()
                self.assertIn('next/next.css', html)
                # Settings has the one way back to the old version.
                self.assertEqual([u for u in OLD_LINK.findall(html) if url != "/settings/"], [])

    def test_pages_with_nothing_in_the_database(self):
        for model in (Usage, Pen, Ink):
            model.objects.all().delete()
        for url in PAGES:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_a_form_saved_here_lands_here(self):
        r = self.client.post("/usages/add/", {"pen": self.due.pk, "nib": self.nib.pk, "ink": self.red.pk, "begin": "2026-01-01"})
        self.assertRedirects(r, f"/pens/{self.due.pk}/", fetch_redirect_response=False)
        r = self.client.post(f"/usages/{self.now.pk}/end/")
        self.assertRedirects(r, "/usages/", fetch_redirect_response=False)
        self.now.refresh_from_db()
        self.assertEqual(self.now.end, date.today())

    def test_an_undo_after_a_change_here_comes_back_here(self):
        self.client.post(f"/usages/{self.now.pk}/end/")
        html = self.client.get("/usages/").content.decode()
        token = re.search(r'action="/undo/([^/]+)/"', html).group(1)
        r = self.client.post(f"/undo/{token}/", {"next": "/usages/"})
        self.assertRedirects(r, "/usages/", fetch_redirect_response=False)
        self.now.refresh_from_db()
        self.assertIsNone(self.now.end)

    def test_the_old_address_of_the_picker_lands_on_the_picker(self):
        r = self.client.get(f"/dashboard/?pen={self.due.pk}&shuffle=2")
        self.assertEqual(r.status_code, 307)
        self.assertEqual(r["Location"], f"/pick/?pen={self.due.pk}&shuffle=2")
        self.assertEqual(self.client.get("/pick/").status_code, 200)

    def test_a_404_here_keeps_this_look(self):
        with override_settings(DEBUG=False):
            html = self.client.get("/no-such-page/", headers={"Accept": "text/html"}).content.decode()
        self.assertIn("next/next.css", html)

    def test_the_tab_bar_lights_the_place_of_each_page(self):
        """The kit's tab bar (KIT-TABS): one tab marked, sub-pages too, and a page
        behind More (Inkings, the picker, search, settings) lights More."""
        more = 'data-phone data-menu-btn'
        cases = {"/dashboard/": "Desk", "/pens/": "Pens", "/pens/needs-photos/": "Pens", "/inks/": "Inks",
                 "/stats/": "Stats", "/stats/records/": "Stats", "/stats/pairs/": "Stats",
                 "/usages/": more, "/pick/": more, "/search/?q=blue": more, "/settings/": more}
        for url, tab in cases.items():
            html = self.client.get(url).content.decode()
            html = html[html.index('<nav class="kit-tabs"') : html.index("</nav>", html.index('<nav class="kit-tabs"'))]
            with self.subTest(url=url):
                self.assertEqual(html.count('aria-current="page"'), 1)
                lit = html[: html.index('aria-current="page"')]
                lit = lit[lit.rindex('class="kit-tab"') :] + html[html.index('aria-current="page"') :][:400]
                self.assertIn(tab if tab == more else "<span>%s</span>" % tab, lit)

    def test_list_rows_cost_no_query_per_row(self):
        with self.assertNumQueries(self._queries_for("/pens/")):
            self.client.get("/pens/")
        for i in range(20):
            Pen.objects.create(obtained=date(2020, 1, 1), brand=self.pen.brand, model=f"Extra {i}", filling="Piston", age="Modern",
                               obtained_from="shop", out=False, price=10, rotation=self.rot)
        self.client.get("/pens/")
        with self.assertNumQueries(self._queries_for("/pens/")):
            self.client.get("/pens/")

    def _queries_for(self, url):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            self.client.get(url)
        return len(ctx)


@override_settings(STORAGES=PLAIN_STATIC)
class TheCutOver(Seeded):
    """Nov 2026: the new version took the main addresses, the old one is /prev/."""

    def setUp(self):
        self.client.force_login(self.owner)

    def test_the_main_desk_is_the_new_one(self):
        r = self.client.get("/dashboard/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("next/next.css", r.content.decode())

    def test_the_old_version_is_under_prev(self):
        self.assertRedirects(self.client.get("/prev/"), "/prev/dashboard/", fetch_redirect_response=False)
        for url in ("/prev/dashboard/", "/prev/pens/", f"/prev/pens/{self.pen.pk}/", "/prev/history/", "/prev/settings/"):
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 200)
                self.assertNotIn("next/next.css", r.content.decode())

    def test_each_version_leads_to_the_other(self):
        html = self.client.get("/prev/dashboard/").content.decode()
        self.assertIn('href="/dashboard/" class="menu-link" hx-boost="false"', html)
        self.assertIn('href="/dashboard/"', self.client.get("/prev/settings/").content.decode())
        self.assertIn('href="/prev/dashboard/"', self.client.get("/settings/").content.decode())

    def test_a_redirect_in_the_old_version_stays_there(self):
        r = self.client.post(f"/prev/usages/{self.now.pk}/end/")
        self.assertRedirects(r, "/prev/usages/", fetch_redirect_response=False)

    def test_the_weeks_under_next_still_land(self):
        r = self.client.get("/next/")
        self.assertEqual((r.status_code, r["Location"]), (301, "/dashboard/"))
        r = self.client.get("/next/pens/?view=grid")
        self.assertEqual((r.status_code, r["Location"]), (301, "/pens/?view=grid"))
        r = self.client.post(f"/next/usages/{self.now.pk}/end/")
        self.assertEqual((r.status_code, r["Location"]), (308, f"/usages/{self.now.pk}/end/"))


@override_settings(STORAGES=PLAIN_STATIC)
class WhatTheOldPagesHad(Seeded):
    """The things the old pages showed that the new version lacked (Nov 2026)."""

    def setUp(self):
        self.client.force_login(self.owner)

    def test_the_pen_page_edits_the_fill_in_it(self):
        html = self.client.get(f"/pens/{self.pen.pk}/").content.decode()
        self.assertIn(f'href="/usages/{self.now.pk}/edit/">Edit this fill', html)

    def test_a_pen_row_says_its_filling_and_year(self):
        html = self.client.get("/pens/").content.decode()
        self.assertIn('class="pen-facts-nx">Piston, since 2020', html)
        self.rot.in_use = False
        self.rot.save()
        html = self.client.get("/pens/?view=grid").content.decode()
        self.assertIn('<em class="pip">Out</em>', html)

    def test_an_ink_row_says_sample_year_and_moi(self):
        Ink.objects.filter(pk=self.red.pk).update(volume=3, obtained=date(2021, 5, 1), moi_url="https://example.com/moi")
        html = self.client.get("/inks/?view=list&samples=1").content.decode()
        self.assertIn("Red, a sample, 3 ml", html)
        self.assertIn("since 2021", html)
        self.assertIn('href="https://example.com/moi"', html)

    def test_the_desk_lists_more_than_one_due_pen_and_the_days(self):
        brand = Brand.objects.get()
        for n in range(3):
            Pen.objects.create(obtained=date(2021, 1, 1), brand=brand, model=f"Spare {n}", filling="c/c", age="Modern",
                               obtained_from="shop", out=False, price=10, rotation=self.rot)
        html = self.client.get("/dashboard/").content.decode()
        self.assertIn('<h3 class="then-h">Then</h3>', html)
        self.assertIn("Never inked", html)
        self.assertIn("pen-days inked", html)

    def test_the_pick_page_names_a_hard_bottle(self):
        hard = Rotation.objects.create(priority=None, how_often=0, whos="Bottle hard to fill from", in_use=True)
        Ink.objects.filter(pk=self.red.pk).update(rotation=hard)
        html = self.client.get(f"/pick/?pen={self.due.pk}").content.decode()
        self.assertIn("a hard bottle to fill from", html)

    def test_stats_have_the_old_history_years(self):
        html = self.client.get("/stats/").content.decode()
        self.assertIn("Year by year", html)
        self.assertIn("2024: ", html)
        html = self.client.get("/stats/cupboard/").content.decode()
        self.assertIn("Inks added per year", html)
        self.assertIn("Spent on ink per year", html)
        self.assertIn('data-tip-links="See the inkings|/usages/?color=Blue"', html)

    def test_timeline_zooms_and_pairings_link(self):
        self.assertIn('data-tl-zoom="4"', self.client.get("/stats/timeline/").content.decode())
        html = self.client.get("/stats/pairs/").content.decode()
        self.assertIn(f"Open the pen|/pens/{self.pen.pk}/", html)

    def test_a_pen_page_s_year_bars_stay_here(self):
        Usage.objects.create(pen=self.pen, nib=self.nib, ink=self.red, begin=date(2023, 3, 1), end=date(2023, 4, 1))
        html = self.client.get(f"/pens/{self.pen.pk}/").content.decode()
        self.assertIn("data-stack-chart", html)
        self.assertEqual(OLD_LINK.findall(html), [])
        self.assertNotIn("|/prev/", html)


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
                         {"links": "See them|/usages/?began=2024", "url": "/usages/?color=Blue"})

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
        self.assertEqual(skin.to_next("/accounts/google/login/?next=/dashboard/"), "/accounts/google/login/?next=/dashboard/")
        self.assertEqual(skin.to_next("/pens/5/"), "/pens/5/")
        self.assertEqual(skin.to_next("/pens/5/"), "/pens/5/")

    def test_the_river_data_cannot_close_its_script_tag(self):
        from dpypen.items.templatetags.items_extras import json_script_safe

        text = json_script_safe({"a": "</script>&"})
        self.assertNotIn("</script>", text)
        self.assertEqual(json.loads(text), {"a": "</script>&"})
