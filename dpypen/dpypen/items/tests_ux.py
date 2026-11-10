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
