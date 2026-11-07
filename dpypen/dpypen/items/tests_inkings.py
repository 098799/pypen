"""The charts of the ink-ups (PYPEN-10): what they count, and what a mark opens."""

from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from dpypen.items import inkings
from dpypen.items.models import Brand, Ink, Nib, Pen, Rotation, Usage


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_superuser("o", "o@example.com", "x")
        brand = Brand.objects.create(name="Pilot", nationality="Japan")
        rot = Rotation.objects.create(priority=1, how_often=1, whos="Tomek", in_use=True)
        cls.pen = Pen.objects.create(obtained=date(2019, 1, 1), brand=brand, model="Custom 74", filling="Piston", age="Modern", obtained_from="shop", out=False, price=100, rotation=rot)
        cls.pen2 = Pen.objects.create(obtained=date(2019, 1, 1), brand=brand, model="Elite", filling="Piston", age="Modern", obtained_from="shop", out=False, price=100, rotation=rot)
        cls.nib = Nib.objects.create(width="M", cut="Round", material="Gold")
        cls.blue = Ink.objects.create(brand=brand, name="Iroshizuku Asa", color="Blue", obtained_from="shop", how="Bought", volume=50, rotation=rot, used_up=False, price=20)
        cls.red = Ink.objects.create(brand=brand, name="Momiji", color="Red", obtained_from="shop", how="Bought", volume=50, rotation=rot, used_up=False, price=20)
        cls.black = Ink.objects.create(brand=brand, name="Black", color="Black", obtained_from="shop", how="Bought", volume=50, rotation=rot, used_up=False, price=20)
        u = lambda pen, ink, b, e=None: Usage.objects.create(pen=pen, nib=cls.nib, ink=ink, begin=b, end=e)  # noqa: E731
        u(cls.pen, cls.blue, date(2020, 12, 20), date(2021, 1, 20))   # 31 days, over New Year
        u(cls.pen, cls.red, date(2021, 3, 1), date(2021, 3, 4))       # 3 days
        u(cls.pen2, cls.red, date(2021, 3, 2), date(2021, 6, 1))      # 91 days, two pens at once in March
        u(cls.pen2, cls.black, date(2021, 6, 6))                      # still in the pen

    def setUp(self):
        cache.clear()
        self.client.force_login(self.owner)


class Counts(Base):
    TODAY = date(2021, 12, 31)

    def test_an_inking_counts_on_the_day_it_began(self):
        d = inkings.build(None, self.TODAY)
        by_year = {c["key"]: c["n"] for c in d["columns"]}
        self.assertEqual(by_year, {2020: 1, 2021: 3})
        self.assertEqual(d["stats"]["inkings"], 4)

    def test_a_year_narrows_the_counts_but_the_line_still_sees_a_fill_from_before(self):
        d = inkings.build(2021, self.TODAY)
        self.assertEqual(d["stats"]["inkings"], 3)
        self.assertEqual([c["n"] for c in d["columns"]], [0, 0, 2, 0, 0, 1] + [0] * 6)
        self.assertEqual(d["heatmap"], None)
        values = [int(v) for v in d["desk"]["values"].split(",")]
        self.assertEqual(values[0], 1)  # 1 Jan 2021: the fill poured in 2020
        self.assertEqual(d["desk"]["peak"], 2)
        self.assertEqual(values[-1], 1)

    def test_durations_take_ended_fills_only(self):
        d = inkings.build(2021, self.TODAY)["durations"]
        self.assertEqual(d["ended"], 2)
        self.assertEqual([b["n"] for b in d["bars"]], [1, 0, 0, 0, 0, 1, 0])
        self.assertEqual(d["median"], 47)

    def test_stack_folds_colours_into_families_in_order(self):
        d = inkings.build(None, self.TODAY)
        c2021 = next(c for c in d["columns"] if c["key"] == 2021)
        self.assertEqual([s["fam"] for s in c2021["segs"]], ["black", "red"])
        self.assertEqual([s["n"] for s in c2021["segs"]], [1, 2])
        self.assertEqual([f["fam"] for f in d["legend"]], ["black", "blue", "red"])

    def test_every_ink_colour_has_a_family(self):
        from dpypen.items.public import INK_COLOR_HEX

        self.assertEqual(set(inkings.COLOR_ORDER), set(INK_COLOR_HEX))

    def test_a_colour_nobody_named_yet_is_still_counted(self):
        Usage.objects.filter(ink=self.black).update(begin=date(2021, 6, 6))
        Ink.objects.filter(pk=self.black.pk).update(color="Chartreuse")
        d = inkings.build(None, self.TODAY)
        self.assertEqual(d["stats"]["inkings"], 4)
        self.assertIn("other", [f["fam"] for f in d["legend"]])

    def test_a_month_ahead_is_not_a_quiet_month(self):
        d = inkings.build(2021, date(2021, 6, 15))
        self.assertEqual([c.get("ahead") for c in d["columns"]], [False] * 6 + [True] * 6)

    def test_top_lists_rank_by_inkings(self):
        d = inkings.build(None, self.TODAY)
        self.assertEqual({p["id"]: p["n"] for p in d["top_pens"]}, {self.pen.pk: 2, self.pen2.pk: 2})
        self.assertEqual(d["top_inks"][0]["id"], self.red.pk)
        self.assertEqual(d["colors"][0]["name"], "Red")


class Page(Base):
    def test_all_and_a_year(self):
        r = self.client.get("/prev/history/inkings/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Inkings by year")
        self.assertContains(r, "Month by month")
        r = self.client.get("/prev/history/inkings/?y=2021")
        self.assertContains(r, "Inkings by month")
        self.assertNotContains(r, "Month by month")

    def test_an_unknown_year_is_no_filter(self):
        for bad in ("1999", "abc", "٢٠٢١", "20211"):
            r = self.client.get("/prev/history/inkings/", {"y": bad})
            self.assertEqual(r.status_code, 200, bad)
            self.assertContains(r, "Inkings by year")

    def test_no_inkings_at_all(self):
        Usage.objects.all().delete()
        r = self.client.get("/prev/history/inkings/")
        self.assertContains(r, "No inkings to chart yet")
        self.assertNotContains(r, "chart-box")

    def test_a_guest_reads_a_stranger_does_not(self):
        self.client.logout()
        r = self.client.get("/prev/history/inkings/")
        self.assertNotEqual(r.status_code, 200)
        self.assertNotIn(b"Inkings by year", r.content)

    def test_a_new_inking_shows_at_once(self):
        self.assertContains(self.client.get("/prev/history/inkings/?y=2021"), "<b>3</b>")
        Usage.objects.create(pen=self.pen, nib=self.nib, ink=self.red, begin=date(2021, 7, 1), end=date(2021, 7, 2))
        self.assertContains(self.client.get("/prev/history/inkings/?y=2021"), "<b>4</b>")

    def test_the_tab_is_in_the_history_nav(self):
        for u in ("/prev/history/", "/prev/history/calendar/", "/prev/history/gantt/", "/prev/history/matrix/"):
            self.assertContains(self.client.get(u), 'href="/prev/history/inkings/"')

    def test_tips_carry_no_markup_from_the_database(self):
        Ink.objects.filter(pk=self.red.pk).update(name="<img src=x onerror=1>")
        cache.clear()
        for u in ("/prev/history/inkings/", "/prev/history/calendar/", "/prev/history/matrix/"):
            self.assertNotContains(self.client.get(u), "<img src=x")

    def test_query_count_does_not_grow_with_the_rows(self):
        def count():
            cache.clear()
            with CaptureQueriesContext(connection) as c:
                self.client.get("/prev/history/inkings/")
            return len(c)

        before = count()
        for i in range(30):
            Usage.objects.create(pen=self.pen, nib=self.nib, ink=self.blue, begin=date(2019, 1, 1) + timedelta(days=i), end=date(2019, 3, 1))
        self.assertEqual(count(), before)


class ListScope(Base):
    def test_a_year_a_month_a_colour(self):
        total = lambda **q: self.client.get("/api/usages", q).json()["total"]  # noqa: E731
        self.assertEqual(total(began="2021"), 3)
        self.assertEqual(total(began="2021-03"), 2)
        self.assertEqual(total(began="2021-03", color="Red"), 2)
        self.assertEqual(total(color="Blue"), 1)

    def test_blue_is_not_blue_black(self):
        rot = self.blue.rotation
        bb = Ink.objects.create(brand=self.blue.brand, name="BB", color="Blue Black", obtained_from="s", how="Bought", volume=5, rotation=rot, used_up=False, price=20)
        Usage.objects.create(pen=self.pen, nib=self.nib, ink=bb, begin=date(2021, 7, 1), end=date(2021, 7, 2))
        self.assertEqual(self.client.get("/api/usages", {"color": "Blue"}).json()["total"], 1)

    def test_a_wrong_value_is_no_filter(self):
        for bad in ({"began": "2021-13"}, {"began": "0000-01"}, {"began": "x"}, {"color": "Nope"}):
            r = self.client.get("/prev/usages/", bad)
            self.assertEqual(r.status_code, 200, bad)
            self.assertEqual(r.context["scope"]["label"], "", bad)

    def test_the_list_says_what_is_on_and_how_to_leave(self):
        r = self.client.get("/prev/usages/", {"began": "2021-03", "color": "Red"})
        self.assertContains(r, "Red · Mar 2021")
        self.assertContains(r, 'aria-current="true" href="/prev/usages/"')

    def test_an_empty_scope_has_a_way_out(self):
        r = self.client.get("/prev/usages/", {"began": "2018"})
        self.assertContains(r, "No past inking in 2018")


class RecordPages(Base):
    def test_a_pen_page_has_its_bars(self):
        r = self.client.get(f"/prev/pens/{self.pen.pk}/")
        self.assertContains(r, "per year")
        self.assertContains(r, "bar-col")

    def test_an_ink_page_has_its_bars(self):
        r = self.client.get(f"/prev/inks/{self.red.pk}/")
        self.assertContains(r, "per year")

    def test_one_year_is_no_chart(self):
        Usage.objects.all().delete()
        Usage.objects.create(pen=self.pen, nib=self.nib, ink=self.red, begin=date.today(), end=None)
        r = self.client.get(f"/prev/pens/{self.pen.pk}/")
        self.assertNotContains(r, "bar-col")
