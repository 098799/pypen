"""supen and suink as a page under /next/ (PYPEN-12, nextui/turns.py)."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from dpypen.items.models import Brand, Ink, Nib, Pen, Rotation, Usage
from dpypen.items.nextui import turns
from dpypen.items.tests import PLAIN_STATIC


def pen(brand, model, rot):
    return Pen.objects.create(obtained=date(2020, 1, 1), brand=brand, model=model, filling="Piston", age="Modern",
                              obtained_from="shop", out=False, price=100, rotation=rot)


def ink(brand, name, rot, **kw):
    return Ink.objects.create(brand=brand, name=name, color="Blue", obtained_from="shop", how="Bought",
                              rotation=rot, **{"volume": 50, "used_up": False, **kw})


class Turns(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("owner", password="x")
        cls.today = today = date.today()
        b = Brand.objects.create(name="Pelikan", nationality="DE")
        cls.p0 = Rotation.objects.create(priority=0, how_often=100, whos="Tomek", in_use=True)
        cls.p1 = Rotation.objects.create(priority=1, how_often=365, whos="Tomek", in_use=True)
        cls.oz = Rotation.objects.create(priority=2, how_often=365, whos="Ozlem", in_use=True)
        cls.out = Rotation.objects.create(priority=None, how_often=-1, whos="Tomek", in_use=False)
        cls.gone = Rotation.objects.create(priority=4, how_often=-1, whos="Tomek", in_use=False)
        cls.easy = Rotation.objects.create(priority=1, how_often=365, whos="Bottle easy to fill from", in_use=True)
        cls.hard = Rotation.objects.create(priority=2, how_often=730, whos="Bottle hard to fill from", in_use=True)
        nib = Nib.objects.create(width="F", cut="round", material="14k")

        cls.inked = pen(b, "M800", cls.p0)        # inked now
        cls.fresh = pen(b, "M200", cls.p0)        # 50 days resting, turn 100: within 3/4
        cls.due = pen(b, "M400", cls.p0)          # 110 days: within 5/4
        cls.late = pen(b, "M1000", cls.p0)        # 200 days: past
        cls.never = pen(b, "M101N", cls.p0)
        cls.ozlems = pen(b, "M300", cls.oz)
        cls.retired = pen(b, "M600", cls.out)
        cls.defunct = pen(b, "M120", cls.gone)

        cls.blue = ink(b, "4001 Blue", cls.easy)
        cls.black = ink(b, "4001 Black", cls.hard)
        cls.sample = ink(b, "Sample", cls.easy, volume=3)
        cls.empty = ink(b, "Empty", cls.easy, used_up=True)
        cls.fresh_bottle = ink(b, "Fresh", cls.easy)

        def use(p, i, begin, end=None):
            Usage.objects.create(pen=p, ink=i, nib=nib, begin=today - timedelta(days=begin),
                                 end=today - timedelta(days=end) if end is not None else None)

        use(cls.inked, cls.blue, 10)
        use(cls.inked, cls.black, 300, 260)
        use(cls.fresh, cls.black, 80, 50)
        use(cls.due, cls.black, 150, 110)
        use(cls.late, cls.black, 230, 200)
        use(cls.late, cls.black, 400, 380)

    def rows(self, data, key):
        return {str(r["item"].model if hasattr(r["item"], "model") else r["item"].name): r
                for g in data["groups"] if g["key"] == key for r in g["rows"]}

    def test_supen_numbers_and_colours(self):
        rows = self.rows(turns.build("pens", today=self.today), "p0")
        self.assertEqual((rows["M800"]["since"], rows["M800"]["state"], rows["M800"]["fills"]), (0, "now", 2))
        self.assertEqual(rows["M800"]["days"], 10 + 40)        # an open fill counts to today
        self.assertEqual((rows["M200"]["since"], rows["M200"]["state"]), (50, "fresh"))
        self.assertEqual((rows["M400"]["since"], rows["M400"]["state"]), (110, "due"))
        self.assertEqual((rows["M1000"]["since"], rows["M1000"]["state"], rows["M1000"]["fills"]), (200, "late", 2))
        self.assertEqual((rows["M101N"]["since"], rows["M101N"]["state"], rows["M101N"]["days"]), (None, "never", 0))

    def test_sorted_like_supen_dash_o_2(self):
        data = turns.build("pens", today=self.today)
        self.assertEqual([r["item"].model for r in data["groups"][0]["rows"]], ["M800", "M200", "M400", "M1000", "M101N"])
        data = turns.build("pens", sort="fills", today=self.today)
        self.assertEqual(data["groups"][0]["rows"][-1]["fills"], 2)
        data = turns.build("pens", sort="name", today=self.today)
        names = [r["item"].model for r in data["groups"][0]["rows"]]
        self.assertEqual(names, sorted(names, key=lambda n: f"pelikan {n}".lower()))

    def test_groups_and_the_out_chip(self):
        data = turns.build("pens", today=self.today)
        self.assertEqual([g["key"] for g in data["groups"]], ["p0", "ozlem"])  # P1 has no pens; Out only on its own
        self.assertEqual([k for k, _ in data["chips"]], ["", "p0", "p1", "ozlem", "out"])
        out = turns.build("pens", rot="out", today=self.today)
        self.assertEqual([r["item"].model for g in out["groups"] for r in g["rows"]], ["M600"])
        self.assertEqual(out["groups"][0]["rows"][0]["state"], "never")
        self.assertEqual(turns.build("pens", rot="nonsense", sort="nonsense", today=self.today)["rot"], "")

    def test_suink_takes_open_bottles_only(self):
        data = turns.build("inks", today=self.today)
        self.assertEqual([g["key"] for g in data["groups"]], ["easy", "hard"])
        easy = self.rows(data, "easy")
        self.assertEqual(set(easy), {"4001 Blue", "Fresh"})              # no sample, no used-up bottle
        self.assertEqual(easy["4001 Blue"]["state"], "now")
        self.assertEqual(easy["Fresh"]["state"], "never")
        black = self.rows(data, "hard")["4001 Black"]
        self.assertEqual((black["fills"], black["since"], black["state"]), (5, 50, "fresh"))

    @override_settings(STORAGES=PLAIN_STATIC)
    def test_the_pages(self):
        self.client.force_login(self.owner)
        html = self.client.get("/next/supen/").content.decode()
        self.assertIn("Pens' turns", html)
        self.assertIn('class="st st-late">200', html)
        self.assertIn("4001 Blue", html)                                 # what the inked pen holds
        self.assertIn('href="/next/supen/?rot=p0"', html)
        html = self.client.get("/next/supen/?rot=p0&sort=days").content.decode()
        self.assertIn('href="/next/supen/?rot=p0&amp;sort=fills"', html)
        self.assertIn('href="/next/supen/?sort=days">All', html)          # a rotation chip keeps the sort
        self.assertIn('href="/next/supen/?rot=p0&amp;sort=days" aria-current="true">Days inked', html)
        html = self.client.get("/next/suink/").content.decode()
        self.assertIn("Bottles' turns", html)
        self.assertIn("in Pelikan M800", html)

    @override_settings(STORAGES=PLAIN_STATIC)
    def test_cost_does_not_grow_with_rows(self):
        self.client.force_login(self.owner)
        self.client.get("/next/supen/")
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as before:
            self.client.get("/next/supen/")
        b = Brand.objects.get()
        for n in range(10):
            p = pen(b, f"Extra {n}", self.p0)
            Usage.objects.create(pen=p, ink=self.blue, nib=Nib.objects.get(), begin=self.today - timedelta(days=30), end=self.today)
        with CaptureQueriesContext(connection) as after:
            self.client.get("/next/supen/")
        self.assertEqual(len(after), len(before))

    def test_a_stranger_gets_the_door(self):
        for url in ("/next/supen/", "/next/suink/"):
            self.assertNotEqual(self.client.get(url).status_code, 200)
