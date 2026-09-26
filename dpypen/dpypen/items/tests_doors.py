"""The two things whose breakage would cost the most, each walked end to end.

1. The door. The collection is private (commit 7c68668, "Shut the door"), but
   the lock is one decorator per view: a new route that forgets it is open to
   the internet, and nothing would say so. That commit was "verified by walking
   every route signed out" by hand, once. These tests do the walk on every run,
   over every route in items/urls.py, GET and POST, as a stranger and as a
   guest on an invite: a stranger sees the landing page and nothing else, a
   guest may read but never write, and neither changes a single row.

2. Undo. The toast's Undo is the only way back from a fat-fingered delete, and
   it re-saves a JSON snapshot taken before the change. If the snapshot stops
   carrying the samples, or the restore stops keeping the primary key, an
   inking comes back half-empty or not at all — and you find out only when you
   press Undo, which is the moment you need it.
"""

import re
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import serializers
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from dpypen.items import urls as item_urls
from dpypen.items.models import Brand, Ink, InkSwatch, InviteCode, Nib, Pen, PenPhoto, Rotation, Usage, WritingSample
from dpypen.items.tests import PLAIN_STATIC

# What a stranger may be served (a 2xx). Everything else must send them away.
OPEN_TO_ANYONE = {
    "home",
    "robots",
    "pwa_manifest",
    "pwa_sw",
    "pwa_icon",
    "pwa_icon_maskable",
    "invite_activate",  # the "accept this invite?" page, for a valid token
}

# What a guest on an invite may read, on top of the above. A guest never
# writes: every POST must leave the data as it was.
GUEST_READS = {
    "dashboard",
    "history",
    "history_calendar",
    "history_gantt",
    "history_matrix",
    "records",
    "next_inking",
    "search",
    "settings",
    "api_palette",
    "usages_list",
    "pens_list",
    "pens_detail",
    "inks_list",
    "inks_detail",
    "share_pen",
    "share_ink",
    "share_inks_gallery",
    "share_inks_wall",
    "share_pens_wall",
}

# Rows that are the collection. InviteCode is left out on purpose: a guest's
# visit counter moves on every page, and that is the one write a guest makes.
COLLECTION = [Brand, Rotation, Pen, Nib, Ink, Usage, PenPhoto, InkSwatch, WritingSample]


def _collection_state():
    return {m.__name__: serializers.serialize("json", m.objects.order_by("pk")) for m in COLLECTION}


class _Collection(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("owner", password="x")
        brand = Brand.objects.create(name="Pelikan", nationality="Germany")
        rot = Rotation.objects.create(priority=1, how_often=1, whos="Tomek", in_use=True)
        cls.pen = Pen.objects.create(
            obtained=date(2020, 1, 1),
            brand=brand,
            model="M800",
            filling="Piston",
            age="Modern",
            obtained_from="shop",
            out=False,
            price=100,
            rotation=rot,
        )
        cls.ink = Ink.objects.create(
            brand=brand, name="4001 Blue", color="Blue", obtained_from="shop", how="Bought", volume=50, rotation=rot, used_up=False
        )
        cls.nib = Nib.objects.create(width="F", cut="Round", material="Gold")
        cls.usage = Usage.objects.create(pen=cls.pen, nib=cls.nib, ink=cls.ink, begin=date.today() - timedelta(days=5))
        # bulk_create skips the models' save(), which would try to open and
        # resize a real image. The rows only need to exist.
        (cls.photo,) = PenPhoto.objects.bulk_create([PenPhoto(pen=cls.pen, image="pen_photos/a.jpg")])
        (cls.swatch,) = InkSwatch.objects.bulk_create([InkSwatch(ink=cls.ink, image="ink_swatches/a.jpg")])
        (cls.sample,) = WritingSample.objects.bulk_create([WritingSample(usage=cls.usage, image="writing_samples/a.jpg", notes="loops")])
        cls.invite = InviteCode.objects.create(token="guest-token", label="friend")


@override_settings(STORAGES=PLAIN_STATIC, PUBLIC_SHOWCASE=False)
class TheDoor(_Collection):
    def routes(self):
        """Every route in items/urls.py as (name, a concrete URL for it)."""
        by_prefix = {
            "usages": {"pk": self.usage.pk},
            "samples": {"pk": self.sample.pk},
            "pens": {"pk": self.pen.pk, "photo_pk": self.photo.pk},
            "inks": {"pk": self.ink.pk},
            "swatches": {"pk": self.swatch.pk},
            "undo": {"token": "no-such-token"},
            "i": {"token": self.invite.token},
            "p": {"token": self.pen.share_token},
            "k": {"token": self.ink.share_token},
            "supen": {"rotation": 1, "order": 2},
            "suink": {"rotation": 1, "order": 2},
        }
        out = []
        for pattern in item_urls.urlpatterns:
            route = str(pattern.pattern)
            params = by_prefix.get(route.split("/")[0], {})

            def fill(m):
                name = m.group(1)
                self.assertIn(name, params, f"tests_doors does not know how to fill <{name}> in {route!r}; add it to by_prefix")
                return str(params[name])

            url = "/" + re.sub(r"<(?:\w+:)?(\w+)>", fill, route)
            out.append((pattern.name or route, url))
        return out

    def assert_sent_away(self, response, url):
        self.assertFalse(200 <= response.status_code < 300, f"{url} answered {response.status_code}")
        if response.status_code in (301, 302):
            self.assertTrue(
                response["Location"].startswith(settings.LOGIN_URL) or response["Location"] == "/", f"{url} sent a stranger to {response['Location']}"
            )

    def test_a_stranger_sees_the_landing_page_and_nothing_else(self):
        before = _collection_state()
        for name, url in self.routes():
            for method in ("get", "post"):
                with self.subTest(route=name, method=method):
                    response = getattr(Client(), method)(url)
                    if name not in OPEN_TO_ANYONE:
                        self.assert_sent_away(response, url)
        self.assertEqual(_collection_state(), before)

    def test_the_landing_page_itself_shows_none_of_the_collection(self):
        html = Client().get("/").content.decode()
        for private in ("M800", "4001 Blue", self.pen.share_token, self.ink.share_token):
            self.assertNotIn(private, html)

    def test_a_guest_reads_but_never_writes(self):
        guest = Client()
        guest.post(f"/i/{self.invite.token}/")
        before = _collection_state()
        for name, url in self.routes():
            if name in ("invite_activate", "invite_deactivate"):
                continue  # these move the guest's own session, not the collection
            with self.subTest(route=name, method="get"):
                response = guest.get(url)
                if name in GUEST_READS:
                    self.assertEqual(response.status_code, 200, url)
                elif name not in OPEN_TO_ANYONE:
                    self.assert_sent_away(response, url)
            with self.subTest(route=name, method="post"):
                response = guest.post(url, {"pen": self.pen.pk, "ink": self.ink.pk, "nib": self.nib.pk, "begin": "2020-01-01", "model": "Stolen"})
                if name not in OPEN_TO_ANYONE | GUEST_READS:
                    self.assert_sent_away(response, url)
        self.assertEqual(_collection_state(), before)

    def test_a_revoked_invite_is_a_stranger_again(self):
        guest = Client()
        guest.post(f"/i/{self.invite.token}/")
        self.assertEqual(guest.get("/dashboard/").status_code, 200)
        InviteCode.objects.filter(pk=self.invite.pk).update(revoked_at=timezone.now())
        self.assert_sent_away(guest.get("/dashboard/"), "/dashboard/")


@override_settings(STORAGES=PLAIN_STATIC)
class UndoBringsItBack(_Collection):
    def setUp(self):
        self.client.force_login(self.owner)

    def last_token(self, client=None):
        return (client or self.client).session["undo_stack"][-1]["token"]

    def test_an_undone_delete_restores_the_inking_and_its_samples(self):
        usage_before = serializers.serialize("json", [self.usage])
        sample_before = serializers.serialize("json", [self.sample])

        self.client.post(f"/usages/{self.usage.pk}/delete/")
        self.assertFalse(Usage.objects.filter(pk=self.usage.pk).exists())
        self.assertFalse(WritingSample.objects.filter(pk=self.sample.pk).exists())

        self.client.post(f"/undo/{self.last_token()}/")
        self.assertEqual(serializers.serialize("json", Usage.objects.filter(pk=self.usage.pk)), usage_before)
        self.assertEqual(serializers.serialize("json", WritingSample.objects.filter(pk=self.sample.pk)), sample_before)

    def test_an_undone_finish_reopens_the_inking(self):
        self.client.post(f"/usages/{self.usage.pk}/end/")
        self.assertEqual(Usage.objects.get(pk=self.usage.pk).end, date.today())
        self.client.post(f"/undo/{self.last_token()}/")
        self.assertIsNone(Usage.objects.get(pk=self.usage.pk).end)

    def test_an_undone_edit_puts_the_old_values_back(self):
        self.client.post(
            f"/usages/{self.usage.pk}/edit/", {"pen": self.pen.pk, "nib": self.nib.pk, "ink": self.ink.pk, "begin": "2001-02-03", "end": ""}
        )
        self.assertEqual(Usage.objects.get(pk=self.usage.pk).begin, date(2001, 2, 3))
        self.client.post(f"/undo/{self.last_token()}/")
        self.assertEqual(Usage.objects.get(pk=self.usage.pk).begin, self.usage.begin)

    def test_an_undone_create_removes_only_the_new_row(self):
        self.client.post("/usages/add/", {"pen": self.pen.pk, "nib": self.nib.pk, "ink": self.ink.pk, "begin": "2026-01-01", "end": ""})
        self.assertEqual(Usage.objects.count(), 2)
        self.client.post(f"/undo/{self.last_token()}/")
        self.assertEqual(list(Usage.objects.values_list("pk", flat=True)), [self.usage.pk])

    def test_a_token_works_once(self):
        self.client.post(f"/usages/{self.usage.pk}/end/")
        token = self.last_token()
        self.client.post(f"/undo/{token}/")
        Usage.objects.filter(pk=self.usage.pk).update(end=date(2026, 5, 5))  # a later, deliberate change
        self.client.post(f"/undo/{token}/")
        self.assertEqual(Usage.objects.get(pk=self.usage.pk).end, date(2026, 5, 5))

    def test_a_token_is_no_good_in_another_session(self):
        self.client.post(f"/usages/{self.usage.pk}/delete/")
        token = self.last_token()
        other = Client()
        other.force_login(self.owner)
        other.post(f"/undo/{token}/")
        self.assertFalse(Usage.objects.filter(pk=self.usage.pk).exists())

    def test_undo_never_bounces_off_site(self):
        self.client.post(f"/usages/{self.usage.pk}/end/")
        response = self.client.post(f"/undo/{self.last_token()}/", {"next": "//evil.example/"})
        self.assertEqual(response["Location"], "/dashboard/")
