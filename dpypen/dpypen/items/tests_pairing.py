"""The next-inking page: which ink goes in the pen that is due."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from dpypen.items.models import Brand, Ink, Nib, Pen, Rotation, Usage
from dpypen.items.pairing import SHOWN, pick, suggest_inks
from dpypen.items.tests import PLAIN_STATIC

TODAY = date.today()


def ago(days):
    return TODAY - timedelta(days=days)


@override_settings(STORAGES=PLAIN_STATIC)
class NextInking(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("owner", password="x")
        cls.brand = Brand.objects.create(name="Pilot", nationality="Japan")
        cls.p1 = Rotation.objects.create(priority=1, how_often=30, whos="Tomek", in_use=True)
        cls.easy = Rotation.objects.create(priority=1, how_often=100, whos="Bottle easy to fill from", in_use=True)
        cls.hard = Rotation.objects.create(priority=2, how_often=100, whos="Bottle hard to fill from", in_use=True)
        cls.nib = Nib.objects.create(width="F", cut="Round", material="Gold")

        cls.piston = cls.pen("Custom 823", "Piston")
        cls.cc = cls.pen("Custom 74", "c/c")
        cls.desk = cls.pen("Vanishing Point", "c/c")

        cls.blue = cls.ink("Blue Old", "Blue", cls.easy)
        cls.green = cls.ink("Green New", "Green", cls.easy)
        cls.hard_red = cls.ink("Red Hard", "Red", cls.hard)
        cls.on_desk = cls.ink("Black Desk", "Black", cls.easy)
        cls.black_too = cls.ink("Black Two", "Black", cls.easy)
        cls.used_up = cls.ink("Gone", "Brown", cls.easy, used_up=True)
        cls.sample = cls.ink("Sample", "Pink", cls.easy, volume=3)

        # Everything rested the same 300 days (three turns), so only the
        # pairing, the favourite and the penalties separate them.
        for ink in (cls.blue, cls.green, cls.hard_red, cls.black_too):
            cls.use(cls.desk, ink, 320, 300)
        # The piston pen has had the blue before; the green is new to it.
        cls.use(cls.piston, cls.blue, 400, 380)
        # The piston pen is due (rested 60 of 30 days); the desk pen is inked.
        cls.use(cls.piston, cls.blue, 90, 60)
        cls.use(cls.cc, cls.green, 40, 20)   # not due: 20 of 30 days
        cls.use(cls.desk, cls.on_desk, 5, None)

    @classmethod
    def pen(cls, model, filling):
        return Pen.objects.create(
            obtained=date(2020, 1, 1),
            brand=cls.brand,
            model=model,
            filling=filling,
            age="Modern",
            obtained_from="shop",
            out=False,
            price=100,
            rotation=cls.p1,
        )

    @classmethod
    def ink(cls, name, color, rot, used_up=False, volume=50):
        return Ink.objects.create(
            brand=cls.brand, name=name, color=color, obtained_from="shop", how="Bought", volume=volume, rotation=rot, used_up=used_up
        )

    @classmethod
    def use(cls, pen, ink, begin, end):
        Usage.objects.create(pen=pen, nib=cls.nib, ink=ink, begin=ago(begin), end=ago(end) if end is not None else None)

    def rank(self, pen):
        return suggest_inks(pen, TODAY, list(Usage.objects.all()))

    def setUp(self):
        self.client.force_login(self.user)

    def test_only_open_bottles_that_are_not_in_a_pen(self):
        names = {s.ink.name for s in self.rank(self.piston)}
        self.assertEqual(names, {"Blue Old", "Green New", "Red Hard", "Black Two"})

    def test_a_new_pairing_beats_a_repeat_at_equal_rest(self):
        ranked = [s.ink.name for s in self.rank(self.cc)]
        # For the c/c pen the green was the last ink but it is new to nothing;
        # the blue and the red are new pairings and rested longer.
        self.assertLess(ranked.index("Blue Old"), ranked.index("Green New"))
        by_name = {s.ink.name: s for s in self.rank(self.piston)}
        self.assertIn(("good", "new pairing"), by_name["Green New"].reasons)
        self.assertEqual(by_name["Blue Old"].pairings, 2)
        self.assertTrue(any("in this pen 2×" in text for _, text in by_name["Blue Old"].reasons))

    def test_a_hard_bottle_sinks_for_a_piston_but_not_for_a_converter(self):
        piston = [s.ink.name for s in self.rank(self.piston)]
        cc = [s.ink.name for s in self.rank(self.cc)]
        # Same rest, same new pairing: the red is marked down only for the dipper.
        self.assertGreater(piston.index("Red Hard"), piston.index("Black Two"))
        self.assertLess(cc.index("Red Hard"), cc.index("Black Two"))
        red = next(s for s in self.rank(self.piston) if s.ink.name == "Red Hard")
        self.assertIn(("warn", "hard bottle for a piston filler"), red.reasons)

    def test_a_colour_already_on_the_desk_is_marked_down(self):
        black = next(s for s in self.rank(self.cc) if s.ink.name == "Black Two")
        red = next(s for s in self.rank(self.cc) if s.ink.name == "Red Hard")
        self.assertIn(("warn", "black is on the desk"), black.reasons)
        self.assertLess(black.score, red.score)  # same rest, same new pairing

    def test_rest_saturates(self):
        # 300 days is three turns; it counts as two, like any long-rested ink.
        red = next(s for s in self.rank(self.cc) if s.ink.name == "Red Hard")
        self.assertAlmostEqual(red.turns, 3.0)
        self.assertAlmostEqual(red.score, 2.0 + 0.4)

    def test_shuffle_is_a_seeded_draw(self):
        ranked = self.rank(self.cc)
        self.assertEqual(pick(ranked, 0), ranked[:SHOWN])
        self.assertEqual([s.ink.pk for s in pick(ranked, 3)], [s.ink.pk for s in pick(ranked, 3)])

    def test_the_page_opens_on_the_pen_most_due(self):
        r = self.client.get("/next/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["pen"], self.piston)
        html = r.content.decode()
        self.assertIn(f"/usages/add/?pen={self.piston.pk}&amp;ink={self.green.pk}", html)
        self.assertIn("Past their <em>turn</em>", html)

    def test_any_pen_can_be_asked_for(self):
        r = self.client.get(f"/next/?pen={self.desk.pk}")
        self.assertEqual(r.context["pen"], self.desk)
        self.assertIn("Inked now with", r.content.decode())
        self.assertEqual(self.client.get("/next/?pen=99999").status_code, 404)
        self.assertEqual(self.client.get(f"/next/?pen={self.cc.pk}&shuffle=2").status_code, 200)

    def test_the_dashboard_rows_lead_here(self):
        html = self.client.get("/dashboard/").content.decode()
        self.assertIn(f'href="/next/?pen={self.piston.pk}"', html)

    def test_strangers_are_sent_to_sign_in(self):
        self.client.logout()
        r = self.client.get("/next/")
        self.assertNotEqual(r.status_code, 200)
