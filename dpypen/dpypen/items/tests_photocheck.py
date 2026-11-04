"""pen_photo_fill and the owner's check of what it found (/next/pens/photos/check/)."""

import io
import json
import tempfile
from datetime import date
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image

from dpypen.items import enhance
from dpypen.items.models import Brand, Pen, PenPhoto, RejectedPenPhoto, Rotation
from dpypen.items.tests import PLAIN_STATIC

MEDIA = tempfile.mkdtemp(prefix="pypen-photocheck-")


def jpeg(color="navy") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (400, 300), color).save(buf, "JPEG")
    return buf.getvalue()


@override_settings(STORAGES=PLAIN_STATIC, MEDIA_ROOT=MEDIA)
class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("owner", password="x")
        brand = Brand.objects.create(name="Jinhao", nationality="CH")
        rot = Rotation.objects.create(priority=1, how_often=30, whos="Tomek", in_use=True)
        kw = dict(obtained=date(2021, 1, 1), brand=brand, filling="c/c", age="Modern", obtained_from="shop", out=False, price=10, rotation=rot)
        cls.pen = Pen.objects.create(model="992 Demo Blue", **kw)
        cls.other = Pen.objects.create(model="X450 Black", **kw)

    def machine_photo(self, pen=None, url="https://shop.example/992.jpg"):
        ph = PenPhoto(pen=pen or self.pen, kind="main", review="check", source_url=url, source_note="Web photo from shop.example, restyled by Gemini")
        ph.image = ContentFile(jpeg(), name="p.jpg")
        ph.save()
        ph.set_styled(jpeg("teal"))
        return ph


class CheckPage(Base):
    def test_owner_sees_the_photos_waiting(self):
        self.machine_photo()
        self.client.force_login(self.owner)
        r = self.client.get("/next/pens/photos/check/")
        self.assertContains(r, "1 photo to check")
        self.assertContains(r, "992 Demo Blue")
        self.assertContains(r, 'value="wrong"')
        self.assertContains(r, "https://shop.example/992.jpg")

    def test_a_stranger_is_sent_to_log_in(self):
        r = self.client.get("/next/pens/photos/check/")
        self.assertEqual(r.status_code, 302)

    def test_right_keeps_it(self):
        ph = self.machine_photo()
        self.client.force_login(self.owner)
        r = self.client.post(f"/next/pens/{self.pen.pk}/photos/{ph.pk}/verdict/", {"verdict": "ok"})
        self.assertRedirects(r, "/next/pens/photos/check/", fetch_redirect_response=False)
        ph.refresh_from_db()
        self.assertEqual(ph.review, "ok")
        self.assertContains(self.client.get("/next/pens/photos/check/"), "Nothing to check")

    def test_wrong_deletes_it_and_blocks_its_source(self):
        ph = self.machine_photo()
        files = [Path(f.path) for f in (ph.image, ph.thumbnail, ph.image_styled, ph.styled_thumbnail)]
        self.client.force_login(self.owner)
        self.client.post(f"/next/pens/{self.pen.pk}/photos/{ph.pk}/verdict/", {"verdict": "wrong"})
        self.assertFalse(PenPhoto.objects.filter(pk=ph.pk).exists())
        self.assertEqual(list(self.pen.rejected_photos.values_list("source_url", flat=True)), ["https://shop.example/992.jpg"])
        self.assertFalse(any(f.exists() for f in files))

    def test_wrong_on_a_drawn_photo_blocks_drawing_again(self):
        ph = self.machine_photo(url="")
        self.client.force_login(self.owner)
        self.client.post(f"/next/pens/{self.pen.pk}/photos/{ph.pk}/verdict/", {"verdict": "wrong"})
        self.assertTrue(self.pen.rejected_photos.filter(source_url=RejectedPenPhoto.GENERATED).exists())

    def test_verdict_is_post_only_and_for_the_owner(self):
        ph = self.machine_photo()
        url = f"/next/pens/{self.pen.pk}/photos/{ph.pk}/verdict/"
        self.assertEqual(self.client.post(url, {"verdict": "wrong"}).status_code, 302)
        self.assertTrue(PenPhoto.objects.filter(pk=ph.pk).exists())
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_next_must_stay_on_the_site(self):
        ph = self.machine_photo()
        self.client.force_login(self.owner)
        r = self.client.post(f"/next/pens/{self.pen.pk}/photos/{ph.pk}/verdict/", {"verdict": "ok", "next": "https://evil.example/"})
        self.assertRedirects(r, "/next/pens/photos/check/", fetch_redirect_response=False)

    def test_pen_page_and_desk_ask(self):
        self.machine_photo()
        self.client.force_login(self.owner)
        page = self.client.get(f"/next/pens/{self.pen.pk}/")
        self.assertContains(page, "Is this your pen?")
        self.assertContains(page, 'name="next" value="/next/pens/%d/"' % self.pen.pk)
        self.assertContains(self.client.get("/next/"), "1 photo to check")

    def test_owners_own_photo_is_not_asked_about(self):
        ph = PenPhoto(pen=self.pen, kind="main")
        ph.image = ContentFile(jpeg(), name="p.jpg")
        ph.save()
        self.client.force_login(self.owner)
        self.assertNotContains(self.client.get(f"/next/pens/{self.pen.pk}/"), "Is this your pen?")


class FillCommand(Base):
    def refs(self, pen, urls):
        root = Path(tempfile.mkdtemp(prefix="pypen-refs-"))
        d = root / str(pen.pk)
        d.mkdir()
        cands = []
        for i, url in enumerate(urls):
            (d / f"c{i}.jpg").write_bytes(jpeg())
            cands.append({"file": f"c{i}.jpg", "url": url, "page": "https://www.shop.example/p", "title": ""})
        (d / "meta.json").write_text(json.dumps({"candidates": cands}))
        return root

    def test_list_names_the_pens_without_photos_and_their_rejects(self):
        RejectedPenPhoto.objects.create(pen=self.pen, source_url="https://bad.example/x.jpg")
        self.machine_photo(pen=self.other)
        out = io.StringIO()
        call_command("pen_photo_fill", "--list", stdout=out)
        pens = json.loads(out.getvalue())["pens"]
        self.assertEqual([p["id"] for p in pens], [self.pen.pk])
        self.assertEqual(pens[0]["rejected"], ["https://bad.example/x.jpg"])

    def test_a_web_photo_is_restyled_and_waits_for_a_check(self):
        root = self.refs(self.pen, ["https://a.example/1.jpg", "https://a.example/2.jpg"])
        with (
            mock.patch.object(enhance, "pick_reference", return_value=(1, "the blue one")),
            mock.patch.object(enhance, "generate_catalog_shot", return_value=jpeg("teal")) as gen,
        ):
            call_command("pen_photo_fill", "--refs", str(root), "--pen", str(self.pen.pk), stdout=io.StringIO(), stderr=io.StringIO())
        gen.assert_called_once()
        ph = self.pen.photos.get()
        self.assertEqual((ph.review, ph.kind, ph.source_url), ("check", "main", "https://a.example/2.jpg"))
        self.assertEqual(ph.source_note, "Web photo from shop.example, restyled by Gemini")
        self.assertTrue(ph.image_styled and ph.styled_thumbnail)

    def test_rejected_sources_are_not_offered_to_the_judge(self):
        RejectedPenPhoto.objects.create(pen=self.pen, source_url="https://a.example/1.jpg")
        root = self.refs(self.pen, ["https://a.example/1.jpg", "https://a.example/2.jpg"])
        with (
            mock.patch.object(enhance, "pick_reference", return_value=(-1, "none")) as judge,
            mock.patch.object(enhance, "generate_from_name", return_value=jpeg()),
        ):
            call_command("pen_photo_fill", "--refs", str(root), "--pen", str(self.pen.pk), stdout=io.StringIO(), stderr=io.StringIO())
        self.assertEqual(len(judge.call_args.args[1]), 1)

    def test_no_fitting_photo_draws_from_the_name_and_says_so(self):
        root = self.refs(self.pen, ["https://a.example/1.jpg"])
        with (
            mock.patch.object(enhance, "pick_reference", return_value=(-1, "wrong colour")),
            mock.patch.object(enhance, "generate_from_name", return_value=jpeg()),
        ):
            call_command("pen_photo_fill", "--refs", str(root), "--pen", str(self.pen.pk), stdout=io.StringIO(), stderr=io.StringIO())
        ph = self.pen.photos.get()
        self.assertEqual((ph.review, ph.source_url), ("check", ""))
        self.assertIn("not a photo", ph.source_note)

    def test_a_rejected_drawing_is_not_drawn_again(self):
        RejectedPenPhoto.objects.create(pen=self.pen, source_url=RejectedPenPhoto.GENERATED)
        root = self.refs(self.pen, [])
        with mock.patch.object(enhance, "pick_reference", return_value=(-1, "none")), mock.patch.object(enhance, "generate_from_name") as draw:
            call_command("pen_photo_fill", "--refs", str(root), "--pen", str(self.pen.pk), stdout=io.StringIO(), stderr=io.StringIO())
        draw.assert_not_called()
        self.assertFalse(self.pen.photos.exists())
