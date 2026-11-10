"""The UX pass of 10 Nov 2026 (AUDIT.md "UX pass", U1-U39): what each fix holds."""

from datetime import date, timedelta

from django.test import override_settings

from dpypen.items.models import Usage
from dpypen.items.tests import PLAIN_STATIC
from dpypen.items.tests_next import Seeded


@override_settings(STORAGES=PLAIN_STATIC)
class BackWhereItCameFrom(Seeded):
    """U1, U5: a form ends on the page it was opened from, or on the record."""

    def setUp(self):
        self.client.force_login(self.owner)

    def test_finish_on_the_desk_stays_on_the_desk(self):
        r = self.client.post(f"/usages/{self.now.pk}/end/", {"next": "/dashboard/"})
        self.assertRedirects(r, "/dashboard/", fetch_redirect_response=False)
        self.now.refresh_from_db()
        self.assertEqual(self.now.end, date.today())

    def test_finish_on_the_pen_page_stays_there(self):
        page = f"/pens/{self.pen.pk}/"
        r = self.client.post(f"/usages/{self.now.pk}/end/", HTTP_REFERER="http://testserver" + page)
        self.assertRedirects(r, page, fetch_redirect_response=False)

    def test_the_desk_and_the_pen_page_send_where_they_are(self):
        for url in ("/dashboard/", f"/pens/{self.pen.pk}/"):
            with self.subTest(url=url):
                self.assertContains(self.client.get(url), f'name="next" value="{url}"')

    def test_never_off_the_site(self):
        for bad in ("https://evil.example/", "//evil.example/", "/\\evil.example"):
            with self.subTest(bad=bad):
                u = Usage.objects.create(pen=self.due, nib=self.nib, ink=self.red, begin=date.today())
                r = self.client.post(f"/usages/{u.pk}/end/", {"next": bad})
                self.assertRedirects(r, "/usages/", fetch_redirect_response=False)

    def test_an_edited_inking_goes_back_to_the_page_it_was_opened_from(self):
        page = f"/pens/{self.pen.pk}/"
        form = self.client.get(f"/usages/{self.now.pk}/edit/", HTTP_REFERER="http://testserver" + page)
        self.assertContains(form, f'name="next" value="{page}"')
        r = self.client.post(
            f"/usages/{self.now.pk}/edit/",
            {"pen": self.pen.pk, "nib": self.nib.pk, "ink": self.ink.pk, "begin": (date.today() - timedelta(days=5)).isoformat(), "next": page},
        )
        self.assertRedirects(r, page, fetch_redirect_response=False)

    def test_a_deleted_inking_never_goes_back_to_its_own_page(self):
        r = self.client.post(f"/usages/{self.now.pk}/delete/", HTTP_REFERER=f"http://testserver/usages/{self.now.pk}/edit/")
        self.assertRedirects(r, "/usages/", fetch_redirect_response=False)

    def test_a_new_pen_and_a_saved_pen_land_on_the_pen(self):
        data = {
            "brand": self.pen.brand_id,
            "model": "M1000",
            "finish": "",
            "obtained": "2026-11-01",
            "filling": "Piston",
            "age": "Modern",
            "obtained_from": "shop",
            "price_0": "100",
            "price_1": "PLN",
            "rotation": self.rot.pk,
        }
        r = self.client.post("/pens/add/", data)
        pen = self.pen.__class__.objects.get(model="M1000")
        self.assertRedirects(r, f"/pens/{pen.pk}/", fetch_redirect_response=False)
        r = self.client.post(f"/pens/{pen.pk}/edit/", {**data, "finish": "Black"})
        self.assertRedirects(r, f"/pens/{pen.pk}/", fetch_redirect_response=False)

    def test_a_saved_ink_lands_on_the_ink(self):
        data = {
            "brand": self.ink.brand_id,
            "line": "",
            "name": "Royal",
            "color": "Blue",
            "obtained": "2026-11-01",
            "obtained_from": "shop",
            "how": "Bought",
            "price_0": "30",
            "price_1": "PLN",
            "volume": "50",
            "rotation": self.rot.pk,
            "moi_url": "",
        }
        r = self.client.post("/inks/add/", data)
        ink = self.ink.__class__.objects.get(name="Royal")
        self.assertRedirects(r, f"/inks/{ink.pk}/", fetch_redirect_response=False)
        r = self.client.post(f"/inks/{ink.pk}/edit/", data)
        self.assertRedirects(r, f"/inks/{ink.pk}/", fetch_redirect_response=False)


class PhoneWidth(Seeded):
    def test_the_record_hero_cannot_grow_past_the_phone(self):
        """U2: one auto column grew to the thumbnail strip."""
        from pathlib import Path

        css = (Path(__file__).resolve().parent / "static/items/next/next.css").read_text()
        self.assertIn(".rec-hero { display: grid; grid-template-columns: minmax(0, 1fr);", css)


@override_settings(STORAGES=PLAIN_STATIC)
class InkingForm(Seeded):
    """U4, U15."""

    def setUp(self):
        self.client.force_login(self.owner)

    def test_an_inking_of_a_used_up_ink_can_still_be_saved(self):
        self.red.used_up = True
        self.red.save()
        page = self.client.get(f"/usages/{self.old.pk}/edit/").content.decode()
        self.assertIn(f'value="{self.red.pk}" selected', page)
        self.assertIn("Ruby · used up", page)
        r = self.client.post(f"/usages/{self.old.pk}/edit/", {"pen": self.due.pk, "nib": self.nib.pk, "ink": self.red.pk,
                                                             "begin": "2024-01-10", "end": "2024-02-11"})
        self.assertEqual(r.status_code, 302)
        self.old.refresh_from_db()
        self.assertEqual(self.old.end, date(2024, 2, 11))

    def test_a_sample_can_be_inked(self):
        from dpypen.items.models import Ink
        vial = Ink.objects.create(brand=self.ink.brand, name="Vial", color="Blue", obtained_from="swap", how="Bought",
                                  volume=2, rotation=self.rot, used_up=False)
        page = self.client.get(f"/usages/add/?ink={vial.pk}").content.decode()
        self.assertIn(f'value="{vial.pk}" selected', page)

    def test_a_used_up_ink_is_not_offered_for_a_new_inking(self):
        self.red.used_up = True
        self.red.save()
        self.assertNotIn("Ruby", self.client.get("/usages/add/").content.decode())

    def test_finished_before_inked_is_refused(self):
        r = self.client.post("/usages/add/", {"pen": self.due.pk, "nib": self.nib.pk, "ink": self.red.pk,
                                              "begin": "2026-03-10", "end": "2026-03-01"})
        self.assertContains(r, "Finished before it was inked")

    def test_an_inked_pen_says_so_and_can_finish_the_old_fill(self):
        self.assertContains(self.client.get("/usages/add/"), "M800 · inked: Pelikan 4001 Blue")
        data = {"pen": self.pen.pk, "nib": self.nib.pk, "ink": self.red.pk, "begin": date.today().isoformat()}
        r = self.client.post("/usages/add/", data)
        self.assertContains(r, "is inked with Pelikan 4001 Blue")
        self.assertContains(r, 'name="finish_open"')
        self.assertEqual(Usage.objects.filter(pen=self.pen, end__isnull=True).count(), 1)
        r = self.client.post("/usages/add/", {**data, "finish_open": "on"})
        self.assertEqual(r.status_code, 302)
        self.now.refresh_from_db()
        self.assertEqual(self.now.end, date.today())
        self.assertEqual(Usage.objects.filter(pen=self.pen, end__isnull=True).count(), 1)


@override_settings(STORAGES=PLAIN_STATIC)
class NewBrandAndDefaults(Seeded):
    """U3, U14."""

    PEN = {"model": "Opus 88", "finish": "", "obtained": "2026-11-01", "filling": "Eyedropper", "age": "Modern",
           "obtained_from": "shop", "price_0": "300", "price_1": "PLN"}

    def setUp(self):
        self.client.force_login(self.owner)

    def test_a_pen_of_a_new_brand(self):
        from dpypen.items.models import Brand, Pen
        r = self.client.post("/pens/add/", {**self.PEN, "rotation": self.rot.pk, "brand": "", "new_brand": "Opus 88"})
        self.assertContains(r, "Where is it from?")
        self.assertFalse(Brand.objects.filter(name="Opus 88").exists())
        r = self.client.post("/pens/add/", {**self.PEN, "rotation": self.rot.pk, "brand": "", "new_brand": "Opus 88",
                                            "new_brand_country": "TW"})
        pen = Pen.objects.get(model="Opus 88")
        self.assertEqual((pen.brand.name, pen.brand.nationality), ("Opus 88", "TW"))
        self.assertEqual(r.status_code, 302)

    def test_a_known_name_is_the_known_brand(self):
        from dpypen.items.models import Brand, Pen
        self.client.post("/pens/add/", {**self.PEN, "rotation": self.rot.pk, "brand": "", "new_brand": "pelikan"})
        self.assertEqual(Pen.objects.get(model="Opus 88").brand, self.pen.brand)
        self.assertEqual(Brand.objects.count(), 1)

    def test_no_brand_at_all_says_how(self):
        r = self.client.post("/pens/add/", {**self.PEN, "rotation": self.rot.pk, "brand": ""})
        self.assertContains(r, "Pick a brand, or write a new one below.")

    def test_an_ink_of_a_new_brand(self):
        from dpypen.items.models import Ink
        r = self.client.post("/inks/add/", {"brand": "", "new_brand": "Ferris Wheel Press", "new_brand_country": "US",
                                            "line": "", "name": "Brush Fire", "color": "Red", "obtained": "2026-11-01",
                                            "obtained_from": "shop", "how": "Bought", "price_0": "30", "price_1": "PLN",
                                            "volume": "38", "rotation": self.rot.pk, "moi_url": ""})
        self.assertEqual(r.status_code, 302, r.context["form"].errors if r.context else "")
        self.assertEqual(Ink.objects.get(name="Brush Fire").brand.name, "Ferris Wheel Press")

    def test_the_add_forms_start_with_today_and_choose(self):
        today = date.today().isoformat()
        for url in ("/pens/add/", "/inks/add/"):
            with self.subTest(url=url):
                page = self.client.get(url).content.decode()
                self.assertIn(f'value="{today}"', page)
                self.assertNotIn("---------", page)
                self.assertIn("A new brand", page)
        self.assertRegex(self.client.get("/inks/add/").content.decode(), r'value="Bought"[^>]*checked')


class SmallFixes(Seeded):
    def test_no_css_variable_points_at_itself(self):
        """U13: `.kit-set { --bad: var(--bad) }` was invalid, so Sign out fell to the kit's dark-theme red (2.8:1)."""
        import re
        from pathlib import Path
        css = (Path(__file__).resolve().parent / "static/items/next/next.css").read_text()
        self.assertEqual([m.group(0) for m in re.finditer(r"(--[\w-]+):\s*var\(\1\)", css)], [])

    def test_photo_pickers_can_choose_from_the_library(self):
        """U8: capture= opens the camera only on a phone."""
        from pathlib import Path
        root = Path(__file__).resolve().parent / "templates/next"
        self.assertEqual([str(p) for p in root.rglob("*.html") if "capture=" in p.read_text()], [])


@override_settings(STORAGES=PLAIN_STATIC)
class OneRuleForPastTheirTurn(Seeded):
    """U6: supen said 4 of 14 past their turn where Stats, Rotation said 12: one counted past 5/4 of the turn."""

    def test_supen_counts_past_the_turn_like_rotation(self):
        from dpypen.items.nextui import turns
        # due: last fill ended 2024-02-10, turn 30 days: past it, and past 5/4 of it.
        g = turns.build("pens")["groups"][0]
        self.assertEqual(g["past"], 1)
        Usage.objects.create(pen=self.due, nib=self.nib, ink=self.red, begin=date.today() - timedelta(days=60),
                             end=date.today() - timedelta(days=33))
        g = turns.build("pens")["groups"][0]
        self.assertEqual((g["past"], g["late"]), (1, 0))   # 33 days: past the 30-day turn, not yet late

    def test_turns_is_a_stats_page(self):
        self.client.force_login(self.owner)
        html = self.client.get("/supen/").content.decode()
        self.assertRegex(html, r'href="/stats/" data-match="/stats /supen /suink" aria-current="page"')
        self.assertIn('href="/supen/" aria-current="true">Turns', html)


class Charts(Seeded):
    def test_a_crowded_column_chart_labels_every_fifth_and_marks_the_peak(self):
        """U7, U22."""
        from dpypen.items.nextui import stats
        cols = stats.columns([(f"’{y % 100:02d}", y - 2000, str(y)) for y in range(2005, 2027)])
        self.assertEqual([c["label"] for c in cols if c["lab"]], ["’06", "’11", "’16", "’21", "’26"])
        self.assertEqual([c["n"] for c in cols if c["mark"]], [26])
        few = stats.columns([("a", 1, ""), ("b", 5, ""), ("c", 2, "")])
        self.assertTrue(all(c["lab"] and c["mark"] for c in few))
        self.assertEqual([c["short"] for c in few if c["edge"]], ["5", "2"])
        flat = stats.columns([(str(y), 5 if y > 2010 else 1, "") for y in range(2000, 2020)])
        self.assertEqual([c["label"] for c in flat if c["mark"]], ["2019"])
        self.assertEqual((stats.compact(12345), stats.compact(1500), stats.compact(999)), ("12k", "1.5k", "999"))


@override_settings(STORAGES=PLAIN_STATIC)
class InkDeleteUndo(Seeded):
    def test_a_deleted_ink_comes_back_with_its_inkings(self):
        """U18: the ink and its inkings went for good, with a confirm; now at once with an Undo."""
        from dpypen.items import undo
        from dpypen.items.models import Ink
        self.client.force_login(self.owner)
        page = self.client.get(f"/inks/{self.ink.pk}/").content.decode()
        self.assertRegex(page, rf'action="/inks/{self.ink.pk}/delete/" data-kit-busy>')
        r = self.client.post(f"/inks/{self.ink.pk}/delete/")
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Ink.objects.filter(pk=self.ink.pk).exists())
        token = self.client.session[undo.SESSION_KEY][-1]["token"]
        self.client.post(f"/undo/{token}/", HTTP_REFERER="http://testserver/inks/")
        self.assertTrue(Ink.objects.filter(pk=self.ink.pk).exists())
        self.assertTrue(Usage.objects.filter(pk=self.now.pk, ink=self.ink).exists())


@override_settings(STORAGES=PLAIN_STATIC)
class StatsWords(Seeded):
    def setUp(self):
        self.client.force_login(self.owner)

    def test_the_calendar_has_weekday_heads_and_today(self):
        """U23."""
        html = self.client.get(f"/stats/calendar/?y={date.today().year}").content.decode()
        self.assertEqual(html.count('class="cal-wd"'), 7 * html.count('class="cal-m"'))
        self.assertEqual(html.count('aria-current="date"'), 1)

    def test_ranks_say_fills_and_days(self):
        """U21: `63 2999 d` was two numbers with one word."""
        html = self.client.get("/stats/inkings/").content.decode()
        self.assertRegex(html, r'<span class="rank-v"><b>\d+</b> fills? · \d+ d</span>')
        self.assertIn(">&lt;1w<", html)


class Scatter(Seeded):
    def test_the_cheapest_pen_is_not_clamped(self):
        """U20."""
        from dpypen.items.nextui import stats
        sc = stats._scatter([{"price": 5, "days": 0}, {"price": 6, "days": 3}, {"price": 4000, "days": 900}])
        xs = [p["x"] for p in sc["points"]]
        self.assertEqual(xs[0], 0)
        self.assertGreater(xs[1], 0)
        self.assertEqual([t["label"] for t in sc["xticks"]][:3], ["5", "10", "20"])


class _Refused(Exception):
    status_code = 401


class _NoCredit(Exception):
    pass


@override_settings(STORAGES=PLAIN_STATIC)
class AiFailuresSaySo(Seeded):
    """U24, U25: a refused key or no credit was blamed on the photo, or not said at all."""

    def setUp(self):
        self.client.force_login(self.owner)

    def test_the_words(self):
        from dpypen.items import aierrors
        self.assertEqual(aierrors.kind(_Refused("Error code: 401 - invalid x-api-key")), "key")
        self.assertEqual(aierrors.kind(_NoCredit("Your credit balance is too low")), "credit")
        self.assertEqual(aierrors.kind(_NoCredit("429 RESOURCE_EXHAUSTED prepay")), "credit")
        self.assertEqual(aierrors.kind(TimeoutError("read timed out")), "")

    def test_the_import_names_a_refused_key(self):
        import io
        from unittest import mock
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (40, 30), "white").save(buf, "JPEG")
        buf.seek(0)
        buf.name = "page.jpg"
        with mock.patch("dpypen.items.notebook.extract_from_image", side_effect=_Refused("invalid x-api-key")):
            r = self.client.post("/import/", {"image": buf}, follow=True)
        self.assertContains(r, "Claude refused the API key")
        self.assertNotContains(r, "sharper photo")

    def test_an_unpolished_upload_says_so(self):
        import io
        import tempfile
        from unittest import mock
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (40, 30), "white").save(buf, "JPEG")
        buf.seek(0)
        buf.name = "pen.jpg"
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media), \
                mock.patch("dpypen.items.enhance.generate_catalog_shot", side_effect=_NoCredit("credit balance is too low")):
            r = self.client.post(f"/pens/{self.due.pk}/photos/add/", {"image": buf, "enhance": "1", "next": "queue"}, follow=True)
        self.assertContains(r, "Saved, not polished. Gemini refused: its credit has run out.")
