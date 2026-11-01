"""Findings from the security pass of 2026-09-25, each pinned by a test.

The site's one way in is Google, and only for the addresses in ALLOWED_EMAILS
(dpypen.items.auth.AllowlistAdapter). These tests keep the other doors shut.
"""

import io
import re
import shutil
import tempfile
from datetime import date
from importlib.metadata import PackageNotFoundError, version
from types import SimpleNamespace
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from dpypen.items.auth import GUEST_SESSION_KEY, _verified_allowed
from dpypen.items.models import Brand, InviteCode, Pen, PenPhoto, Rotation
from dpypen.items.tests import PLAIN_STATIC


class AdminHasNoPasswordDoor(TestCase):
    """/admin/ used to take a username and password.

    That skipped the allowlist: the database still holds an `admin` superuser
    with a usable password from before Google sign-in, and the form was open
    to the internet with only nginx's rate limit in front of it. The admin
    login now sends a stranger to Google, like every other page.
    """

    @classmethod
    def setUpTestData(cls):
        get_user_model().objects.create_superuser("admin", "admin@example.com", "correct horse")

    def test_the_login_page_sends_a_stranger_to_google(self):
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(settings.LOGIN_URL))

    def test_a_right_password_does_not_sign_in(self):
        response = self.client.post("/admin/login/", {"username": "admin", "password": "correct horse", "next": "/admin/"})
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(response["Location"].startswith(settings.LOGIN_URL))

    def test_allauths_own_form_takes_no_password_either(self):
        # SOCIALACCOUNT_ONLY: /accounts/login/ offers Google and nothing else.
        for login in ("admin", "admin@example.com"):
            self.client.post("/accounts/login/", {"login": login, "password": "correct horse"})
            self.assertNotIn("_auth_user_id", self.client.session, login)

    def test_the_admin_itself_is_still_closed(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)


# The first release with no known advisory, as pip-audit saw bae's venv on
# 2026-09-25. Only what the running site imports or parses input with; the dev
# tools in the same venv (black, pytest, click, pygments, setuptools) never see
# a request. requirements.txt pins these; the test keeps an old venv from
# passing for a new one.
SECURITY_FLOORS = {
    "Django": "6.0.8",  # 11 advisories in 6.0.4, among them session and cache header leaks
    "pillow": "13.0.0",  # 14 more decoder advisories in 12.3.0 (pip-audit, 2026-11-01)
    "djangorestframework": "3.18.2",
    "sqlparse": "0.6.0",
    "PyJWT": "2.15.1",  # allauth verifies Google's id_token with it
    "cryptography": "50.0.2",
    "urllib3": "2.8.0",
    "requests": "2.33.1",
    "idna": "3.15",
    "pyasn1": "0.6.5",
    "certifi": "2026.10.18",
    "anyio": "4.14.2",
}


def _parts(v):
    return tuple(int(n) for n in re.findall(r"\d+", v)[:3])


class DependenciesAreAboveTheirAdvisories(TestCase):
    def test_installed_versions(self):
        stale = []
        for name, floor in SECURITY_FLOORS.items():
            try:
                have = version(name)
            except PackageNotFoundError:
                continue  # a transitive that this venv does not pull in
            if _parts(have) < _parts(floor):
                stale.append(f"{name} {have} < {floor}")
        self.assertEqual(stale, [])


# ---- PYPEN-4, 2026-11-01 -------------------------------------------------


def _login(email, *verified):
    """What allauth hands the adapter after Google: the user and the addresses."""
    return SimpleNamespace(
        user=SimpleNamespace(email=email),
        email_addresses=[SimpleNamespace(email=e, verified=True) for e in verified]
        + [SimpleNamespace(email=email, verified=False)],
    )


@override_settings(ALLOWED_EMAILS={"owner@example.com"})
class GoogleMustVouchForTheAddress(TestCase):
    """The allowlist read the address only. A Google account made on a
    non-Gmail address can carry one it never proved (email_verified false)."""

    def test_a_verified_allowlisted_address_comes_in(self):
        self.assertTrue(_verified_allowed(_login("Owner@Example.com ", "owner@example.com")))

    def test_an_unverified_allowlisted_address_does_not(self):
        self.assertFalse(_verified_allowed(_login("owner@example.com")))

    def test_a_verified_stranger_does_not(self):
        self.assertFalse(_verified_allowed(_login("someone@example.com", "someone@example.com")))


class TheWayBackIsQuoted(TestCase):
    """A closed page sends a stranger to Google with the page in `next`. The
    path went in raw, so its `&` handed allauth's login parameters of the
    stranger's choosing."""

    def test_a_query_stays_inside_next(self):
        response = self.client.get("/pens/?q=a&process=connect")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"], "/accounts/google/login/?next=/pens/%3Fq%3Da%26process%3Dconnect"
        )


class SearchMarksDoNotCutEntities(TestCase):
    """highlight() matched inside the escaped text: "lt" hit &lt;."""

    def test_a_term_inside_an_entity_is_not_marked(self):
        from dpypen.items.templatetags.items_extras import highlight

        self.assertEqual(highlight("Salt <Pilot> & co", "lt"), "Sa<mark>lt</mark> &lt;Pilot&gt; &amp; co")

    def test_the_stored_text_is_escaped_around_a_mark(self):
        from dpypen.items.templatetags.items_extras import highlight

        self.assertEqual(highlight("<b>Blue</b>", "blue"), "&lt;b&gt;<mark>Blue</mark>&lt;/b&gt;")
        self.assertEqual(highlight("<i>x</i>", ""), "&lt;i&gt;x&lt;/i&gt;")


@override_settings(STORAGES=PLAIN_STATIC)
class SigningOutForgetsTheDevice(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("owner", password="x")
        cls.invite = InviteCode.objects.create(token="tok-sign-out", label="friend")

    def test_a_get_does_not_sign_out(self):
        # Any page on the internet could do this with an <img src>.
        self.client.force_login(self.owner)
        self.client.get("/accounts/logout/")
        self.assertIn("_auth_user_id", self.client.session)

    def test_the_post_signs_out_and_clears_the_site(self):
        self.client.force_login(self.owner)
        r = self.client.post("/accounts/logout/")
        self.assertEqual(r.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(r["Clear-Site-Data"], '"cache", "storage"')

    def test_a_guest_leaving_clears_the_site(self):
        self.client.post(f"/i/{self.invite.token}/")
        self.assertIn(GUEST_SESSION_KEY, self.client.session)
        r = self.client.post("/i/leave/")
        self.assertNotIn(GUEST_SESSION_KEY, self.client.session)
        self.assertEqual(r["Clear-Site-Data"], '"cache", "storage"')

    def test_accepting_an_invite_is_a_full_page_load(self):
        # An hx-boost swap replaced #main only: the new guest kept the
        # stranger's header and had no tab bar until a reload.
        body = self.client.get(f"/i/{self.invite.token}/").content.decode()
        form = re.search(r"<form method=\"post\"[^>]*>", body).group(0)
        self.assertIn('hx-boost="false"', form)

    def test_an_ordinary_page_clears_nothing(self):
        self.client.force_login(self.owner)
        self.assertNotIn("Clear-Site-Data", self.client.get("/dashboard/"))


@override_settings(STORAGES=PLAIN_STATIC)
class EveryAnswerCarriesThePolicy(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("owner", password="x")

    def test_the_landing_page(self):
        r = self.client.get("/")
        csp = r["Content-Security-Policy"]
        for part in ("default-src 'self'", "object-src 'none'", "base-uri 'self'",
                     "frame-ancestors 'none'", "img-src 'self' data: blob:", "font-src 'self'"):
            self.assertIn(part, csp)
        self.assertIn("camera=()", r["Permissions-Policy"])
        self.assertEqual(r["X-Frame-Options"], "DENY")
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")

    def test_a_private_page_is_not_for_shared_caches(self):
        self.client.force_login(self.owner)
        self.assertIn("private", self.client.get("/dashboard/")["Cache-Control"])
        self.assertIn("no-cache", self.client.get("/dashboard/")["Cache-Control"])  # kit §5.3

    def test_the_service_worker_keeps_its_own_cache_header(self):
        self.assertEqual(self.client.get("/sw.js")["Cache-Control"], "no-cache")

    def test_the_walls_load_no_font_from_google(self):
        # font-src 'self' would block it, and it told Google who looked.
        self.client.force_login(self.owner)
        for url in ("/pub/pens/wall/", "/pub/inks/wall/"):
            body = self.client.get(url).content.decode()
            self.assertNotIn("fonts.googleapis.com", body, url)
            self.assertIn("fonts", body, url)


def _png(size, mode="RGB"):
    buf = io.BytesIO()
    Image.new(mode, size).save(buf, format="PNG")
    return buf.getvalue()


@override_settings(STORAGES=PLAIN_STATIC)
class UploadsMustBePhotos(TestCase):
    """Every upload route re-encodes through Pillow (so no EXIF survives); a
    file Pillow cannot read was a 500 that lost the whole batch."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("owner", password="x")
        rot = Rotation.objects.create(priority=1, how_often=1, whos="T", in_use=True)
        cls.pen = Pen.objects.create(
            obtained=date(2020, 1, 1), brand=Brand.objects.create(name="Pelikan", nationality="Germany"),
            model="M800", filling="Piston", age="Modern", obtained_from="shop", out=False, price=100,
            rotation=rot)

    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        patcher = override_settings(MEDIA_ROOT=self.media)
        patcher.enable()
        self.addCleanup(patcher.disable)
        self.client.force_login(self.owner)

    def _add(self, *files):
        return self.client.post(f"/pens/{self.pen.pk}/photos/add/", {"image": list(files)}, follow=True)

    def test_a_good_photo_goes_in_a_bad_one_is_named(self):
        r = self._add(SimpleUploadedFile("good.png", _png((40, 30)), "image/png"),
                      SimpleUploadedFile("notes.pdf", b"%PDF-1.4 not a photo", "image/jpeg"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(PenPhoto.objects.filter(pen=self.pen).count(), 1)
        self.assertContains(r, "notes.pdf")

    def test_a_decompression_bomb_is_refused(self):
        # 64 MP: over the 50 MP cap, under Pillow's own error at 2x.
        r = self._add(SimpleUploadedFile("bomb.png", _png((8000, 8000), "1"), "image/png"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(PenPhoto.objects.count(), 0)

    def test_a_stored_photo_has_no_exif(self):
        buf = io.BytesIO()
        exif = Image.Exif()
        exif[0x010F] = "PhoneMaker"  # Make
        Image.new("RGB", (40, 30)).save(buf, format="JPEG", exif=exif)
        self._add(SimpleUploadedFile("phone.jpg", buf.getvalue(), "image/jpeg"))
        photo = PenPhoto.objects.get()
        with Image.open(photo.image.path) as stored:
            self.assertEqual(dict(stored.getexif()), {})

    def test_a_stray_rotation_is_not_a_500(self):
        self._add(SimpleUploadedFile("good.png", _png((40, 30)), "image/png"))
        photo = PenPhoto.objects.get()
        for bad in ("abc", "45"):
            r = self.client.post(f"/pens/{self.pen.pk}/photos/{photo.pk}/rotate/", {"degrees": bad})
            self.assertEqual(r.status_code, 302, bad)

    def test_the_notebook_sends_a_fresh_jpeg_and_never_a_non_photo(self):
        with mock.patch("dpypen.items.notebook.extract_from_image", return_value=[]) as call:
            self.client.post("/import/", {"image": SimpleUploadedFile("x.heic", b"nope", "image/heic")})
            call.assert_not_called()
            self.client.post("/import/", {"image": SimpleUploadedFile("p.png", _png((50, 40)), "image/png")})
            call.assert_called_once()
            sent, kwargs = call.call_args[0][0], call.call_args[1]
        self.assertEqual(kwargs["media_type"], "image/jpeg")
        self.assertTrue(sent.startswith(b"\xff\xd8"))
