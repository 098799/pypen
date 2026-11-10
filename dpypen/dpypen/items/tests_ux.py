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
