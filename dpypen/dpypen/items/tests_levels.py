"""Ink left: about how much is in each bottle (README "Ink left", levels.py)."""

from datetime import date, timedelta

from django.core import serializers
from django.test import override_settings

from dpypen.items import levels, pairing
from dpypen.items.models import Brand, Ink, InviteCode, Pen, Usage
from dpypen.items.tests import PLAIN_STATIC
from dpypen.items.tests_next import Seeded


def fill(pen, ink, nib, days_ago, length=20):
    begin = date.today() - timedelta(days=days_ago)
    return Usage.objects.create(pen=pen, ink=ink, nib=nib, begin=begin, end=begin + timedelta(days=length))


class Estimate(Seeded):
    """The arithmetic, on the seeded rows: the M800 is a piston (1.4 ml), the
    M200 a c/c (0.8 ml); 4001 Blue (50 ml) has one fill, the open one."""

    def lvl(self, ink):
        ink.refresh_from_db()
        return levels.for_inks([ink])[ink.pk]

    def test_each_fill_takes_its_pens_usual(self):
        self.assertAlmostEqual(self.lvl(self.ink).left, 50 - 1.4)
        fill(self.due, self.ink, self.nib, 100)
        self.assertAlmostEqual(self.lvl(self.ink).left, 50 - 1.4 - 0.8)

    def test_a_pens_own_fill_beats_its_fillings(self):
        Pen.objects.filter(pk=self.pen.pk).update(fill_ml=3.0)
        self.assertAlmostEqual(self.lvl(self.ink).left, 47.0)

    def test_a_look_resets_it_and_only_later_fills_count(self):
        Ink.objects.filter(pk=self.ink.pk).update(level_ml=10.0, level_on=date.today() - timedelta(days=50))
        fill(self.due, self.ink, self.nib, 100)  # before the look: in it already
        fill(self.due, self.ink, self.nib, 20)  # after: taken off
        # the open fill began 5 days ago, after the look too
        self.assertAlmostEqual(self.lvl(self.ink).left, 10 - 0.8 - 1.4)

    def test_never_below_nothing_and_used_up_is_nothing(self):
        sample = Ink.objects.create(
            brand=self.ink.brand, name="Tiny", color="Blue", obtained_from="x", how="Bought", volume=1, rotation=self.rot, used_up=False
        )
        fill(self.pen, sample, self.nib, 40)
        lvl = self.lvl(sample)
        self.assertEqual((lvl.left, lvl.empty, lvl.low, lvl.left_words), (0.0, True, True, "probably empty"))
        Ink.objects.filter(pk=sample.pk).update(used_up=True)
        lvl = self.lvl(sample)
        self.assertEqual((lvl.left, lvl.empty, lvl.low, lvl.pct, lvl.words), (0.0, False, False, 0, "Used up"))

    def test_the_words(self):
        ink = Ink.objects.create(
            brand=self.ink.brand, name="Ten", color="Red", obtained_from="x", how="Bought", volume=10, rotation=self.rot, used_up=False
        )
        self.assertEqual(self.lvl(ink).row_words, "10 ml, full")
        self.assertEqual(self.lvl(ink).words, "About 10 ml left of 10, some 10 fills")
        for days in (300, 200, 100, 90, 80, 70, 60, 50, 40, 30):
            fill(self.due, ink, self.nib, days)  # 8 ml in c/c fills
        lvl = self.lvl(ink)
        self.assertAlmostEqual(lvl.left, 2.0)
        self.assertEqual((lvl.fill, lvl.fills_left, lvl.low), (0.8, 2, False))
        self.assertEqual(lvl.row_words, "about 2 of 10 ml left")
        fill(self.due, ink, self.nib, 20)
        lvl = self.lvl(ink)
        self.assertEqual((lvl.fills_left, lvl.low, lvl.left_words), (1, True, "about a fill"))
        self.assertEqual(lvl.words, "About one fill left, 1.2 ml")

    def test_its_pace_says_how_long_it_lasts(self):
        ink = Ink.objects.create(
            brand=self.ink.brand,
            name="Slow",
            color="Red",
            obtained_from="x",
            how="Bought",
            volume=30,
            rotation=self.rot,
            used_up=False,
            obtained=date.today() - timedelta(days=3000),
        )
        for days in (100, 400, 700):  # 3 c/c fills in three years: 0.8 ml a year
            fill(self.due, ink, self.nib, days)
        lvl = self.lvl(ink)
        self.assertAlmostEqual(lvl.pace, 0.8, places=2)
        self.assertRegex(lvl.lasts, r"^about 3[45] years$")

    def test_the_sql_order_agrees_with_python(self):
        sample = Ink.objects.create(
            brand=self.ink.brand, name="Tiny", color="Blue", obtained_from="x", how="Bought", volume=2, rotation=self.rot, used_up=False
        )
        fill(self.pen, sample, self.nib, 40)
        Ink.objects.filter(pk=self.red.pk).update(level_ml=5.0, level_on=date(2025, 1, 1))
        Pen.objects.filter(pk=self.due.pk).update(fill_ml=2.0)
        fill(self.due, self.red, self.nib, 30)  # after the look: 5 - 2
        inks = list(Ink.objects.all())
        py = levels.for_inks(inks)
        for i in Ink.objects.annotate(left=levels.left_sql()):
            with self.subTest(ink=i.name):
                self.assertAlmostEqual(i.left, py[i.pk].left, places=5)
        order = list(Ink.objects.annotate(left=levels.left_sql()).order_by("left", "pk").values_list("name", flat=True))
        self.assertEqual(order, ["Tiny", "Ruby", "4001 Blue"])

    def test_one_query_whatever_the_number_of_inks(self):
        inks = list(Ink.objects.all())
        with self.assertNumQueries(1):
            levels.for_inks(inks)


@override_settings(STORAGES=PLAIN_STATIC)
class Look(Seeded):
    def setUp(self):
        self.client.force_login(self.owner)

    def look(self, key, **more):
        return self.client.post(f"/inks/{self.ink.pk}/level/", {"look": key, **more})

    def test_a_look_sets_the_level_and_goes_back_with_an_undo(self):
        r = self.look("1/2", next="/inks/")
        self.assertRedirects(r, "/inks/", fetch_redirect_response=False)
        self.ink.refresh_from_db()
        self.assertEqual((self.ink.level_ml, self.ink.level_on), (25.0, date.today()))
        page = self.client.get("/inks/").content.decode()
        self.assertIn("4001 Blue: about 25 ml left.", page)
        self.assertIn("undo", page.lower())

    def test_empty_is_used_up_and_a_level_takes_it_back(self):
        self.look("empty")
        self.ink.refresh_from_db()
        self.assertEqual((self.ink.used_up, self.ink.used_up_when, self.ink.level_ml), (True, date.today(), 0.0))
        self.look("1/4")
        self.ink.refresh_from_db()
        self.assertEqual((self.ink.used_up, self.ink.used_up_when, self.ink.level_ml), (False, None, 12.5))

    def test_forget_goes_back_to_the_estimate(self):
        self.look("3/4")
        self.look("forget")
        self.ink.refresh_from_db()
        self.assertEqual((self.ink.level_ml, self.ink.level_on), (None, None))

    def test_a_word_it_does_not_know_changes_nothing(self):
        self.look("lots")
        self.ink.refresh_from_db()
        self.assertEqual((self.ink.level_ml, self.ink.used_up), (None, False))

    def test_the_undo_puts_the_bottle_back(self):
        from dpypen.items import undo

        before = undo.snapshot(self.ink)
        self.look("empty")
        for obj in serializers.deserialize("json", before):
            obj.save()
        self.ink.refresh_from_db()
        self.assertEqual((self.ink.used_up, self.ink.level_ml), (False, None))

    def test_a_guest_cannot_look_and_a_stranger_neither(self):
        self.client.logout()
        self.assertEqual(self.look("empty").status_code, 302)
        invite = InviteCode.objects.create(token="t" * 20, label="friend")
        self.client.post(f"/i/{invite.token}/")
        self.look("empty")
        self.ink.refresh_from_db()
        self.assertFalse(self.ink.used_up)
        html = self.client.get(f"/inks/{self.ink.pk}/").content.decode()
        self.assertIn("In the bottle", html)
        self.assertNotIn('name="look"', html)

    def test_get_is_refused(self):
        self.assertEqual(self.client.get(f"/inks/{self.ink.pk}/level/").status_code, 405)


@override_settings(STORAGES=PLAIN_STATIC)
class Screens(Seeded):
    """Every screen that shows an ink shows what is left in it."""

    def setUp(self):
        self.client.force_login(self.owner)
        self.sample = Ink.objects.create(
            brand=self.ink.brand, name="Tiny", color="Blue", obtained_from="x", how="Bought", volume=1, rotation=self.rot, used_up=False
        )
        fill(self.due, self.sample, self.nib, 40)

    def test_the_ink_page_has_the_bottle_and_the_look(self):
        html = self.client.get(f"/inks/{self.ink.pk}/").content.decode()
        self.assertIn('class="bottle"', html)
        self.assertIn("--lvl: 97%", html)
        self.assertIn("About 49 ml left of 50, some 34 fills", html)
        self.assertIn('data-new="ink-left"', html)
        for key in ("full", "3/4", "1/2", "1/4", "low", "empty"):
            self.assertIn(f'name="look" value="{key}"', html)
        self.assertNotIn('value="forget"', html)
        sample = self.client.get(f"/inks/{self.sample.pk}/").content.decode()
        self.assertIn('class="bottle is-vial"', sample)
        self.assertIn("In the sample", sample)
        self.assertIn("Probably empty", sample)

    def test_the_lists_rows_and_cards(self):
        rows = self.client.get("/inks/?view=list&samples=1").content.decode()
        self.assertIn("about 49 of 50 ml left", rows)
        self.assertIn('<span class="lvl-low">1 ml, probably empty</span>', rows)
        cards = self.client.get("/inks/?samples=1").content.decode()
        self.assertIn('class="lvl" style="--lvl: 97%"', cards)
        self.assertIn('<span class="lvl-low">Probably empty</span>', cards)

    def test_least_left_sorts_the_list_and_the_json(self):
        html = self.client.get("/inks/?sort=left&samples=1&view=list").content.decode()
        self.assertLess(html.index("Tiny"), html.index("Ruby"))
        self.assertIn("Least left", html)
        items = self.client.get("/api/inks?sort=left&samples=1").json()["items"]
        self.assertEqual([i["name"] for i in items], ["Tiny", "4001 Blue", "Ruby"])
        self.assertEqual((items[0]["left_ml"], items[1]["left_ml"], items[0]["level_checked"]), (0.2, 48.6, None))

    def test_the_desk_lists_what_runs_low(self):
        html = self.client.get("/dashboard/").content.decode()
        self.assertIn("Running low", html)
        self.assertIn(f'action="/inks/{self.sample.pk}/level/"', html)
        self.assertIn('name="look" value="empty"', html)
        self.client.post(f"/inks/{self.sample.pk}/level/", {"look": "empty"})
        self.assertNotIn('id="lowH"', self.client.get("/dashboard/").content.decode())

    def test_a_sample_in_a_pen_now_is_not_marked_from_the_desk(self):
        Usage.objects.create(pen=self.due, nib=self.nib, ink=self.sample, begin=date.today())
        html = self.client.get("/dashboard/").content.decode()
        self.assertIn("in a pen now", html)
        self.assertNotIn(f'action="/inks/{self.sample.pk}/level/"', html)

    def test_suink_says_what_is_left(self):
        Ink.objects.filter(pk=self.ink.pk).update(rotation=self._bottle_rotation())
        html = self.client.get("/suink/").content.decode()
        self.assertIn("About 49 of 50 ml left", html)

    def _bottle_rotation(self):
        from dpypen.items.models import Rotation

        return Rotation.objects.create(priority=1, how_often=365, whos="Bottle easy to fill from", in_use=True)

    def test_the_cupboard_counts_what_was_drunk(self):
        html = self.client.get("/stats/cupboard/").content.decode()
        self.assertIn("Ink drunk", html)
        self.assertIn("Thirstiest pens", html)
        self.assertIn("about <b>98</b> ml left in them, of 100", html)
        self.assertIn("Tiny", html)  # running low

    def test_a_look_shows_on_stats_at_once(self):
        self.client.get("/stats/cupboard/")
        self.client.post(f"/inks/{self.ink.pk}/level/", {"look": "1/2"})
        self.assertIn("about <b>74</b> ml left", self.client.get("/stats/cupboard/").content.decode())

    def test_the_pen_page_and_form(self):
        html = self.client.get(f"/pens/{self.pen.pk}/").content.decode()
        self.assertIn("ml of ink, about 1.4 a fill for a Piston", html)
        form = self.client.get(f"/pens/{self.pen.pk}/edit/").content.decode()
        self.assertIn('name="fill_ml"', form)
        self.assertIn("c/c 0.8, piston 1.4", form)

    def test_the_picker_warns_of_a_bottle_under_a_fill(self):
        Ink.objects.filter(pk=self.red.pk).update(level_ml=1.0, level_on=date.today())
        ranked = pairing.suggest_inks(self.due, date.today(), list(Usage.objects.all()))
        red = next(s for s in ranked if s.ink.pk == self.red.pk)
        self.assertIn(("", "about one fill left"), red.reasons)
        Ink.objects.filter(pk=self.red.pk).update(level_ml=0.5)
        ranked = pairing.suggest_inks(self.due, date.today(), list(Usage.objects.all()))
        red = next(s for s in ranked if s.ink.pk == self.red.pk)
        self.assertIn(("warn", "about 0.5 ml left, under a fill"), red.reasons)

    def test_an_inking_from_a_nearly_empty_bottle_says_so(self):
        Ink.objects.filter(pk=self.red.pk).update(level_ml=2.0, level_on=date.today() - timedelta(days=1))
        self.client.post("/usages/add/", {"pen": self.due.pk, "nib": self.nib.pk, "ink": self.red.pk, "begin": date.today().isoformat()})
        html = self.client.get(f"/pens/{self.due.pk}/").content.decode()
        self.assertIn("About one fill left, 1.2 ml in the bottle.", html)


@override_settings(STORAGES=PLAIN_STATIC)
class PenForm(Seeded):
    def setUp(self):
        self.client.force_login(self.owner)

    def data(self, **more):
        p = self.pen
        return {
            "brand": p.brand_id,
            "model": p.model,
            "obtained": "2020-01-01",
            "filling": p.filling,
            "age": p.age,
            "obtained_from": p.obtained_from,
            "price_0": "1000",
            "price_1": "PLN",
            "rotation": p.rotation_id,
            **more,
        }

    def test_the_new_form_sets_it_and_checks_it(self):
        self.client.post(f"/pens/{self.pen.pk}/edit/", self.data(fill_ml="2.2"))
        self.pen.refresh_from_db()
        self.assertEqual(self.pen.fill_ml, 2.2)
        r = self.client.post(f"/pens/{self.pen.pk}/edit/", self.data(fill_ml="40"))
        self.assertIn("between 0.1 and 10 ml", r.content.decode())

    def test_the_old_form_keeps_it(self):
        Pen.objects.filter(pk=self.pen.pk).update(fill_ml=2.2)
        self.client.post(f"/prev/pens/{self.pen.pk}/edit/", self.data())
        self.pen.refresh_from_db()
        self.assertEqual(self.pen.fill_ml, 2.2)
        self.assertEqual(Brand.objects.count(), 1)
