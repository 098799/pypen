"""Kept pages (items/pagememo.py): a kept page is the page the view would make,
and nothing is kept that must not be.

The test database lives in memory, where the real memo keeps nothing (no file,
no `PRAGMA data_version`), so each test swaps in a memo whose version it moves
itself: `self.changed()` is a commit.
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from dpypen.items import pagememo
from dpypen.items.dbmemo import Memo
from dpypen.items.models import Brand, Ink, Nib, Pen, Rotation, Usage
from dpypen.items.tests import PLAIN_STATIC

CSRF = "AbCdEfGhIjKlMnOpQrStUvWxYz012345"


@override_settings(STORAGES=PLAIN_STATIC)
class PageMemoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser("owner", password="x")
        brand = Brand.objects.create(name="Pelikan", nationality="Germany")
        rot = Rotation.objects.create(priority=1, how_often=30, whos="Tomek", in_use=True)
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
            brand=brand,
            name="4001 Blue",
            color="Blue",
            obtained_from="shop",
            how="Bought",
            volume=50,
            rotation=rot,
            used_up=False,
        )
        nib = Nib.objects.create(width="F", cut="Round", material="Gold")
        cls.usage = Usage.objects.create(pen=cls.pen, nib=nib, ink=cls.ink, begin=date.today() - timedelta(days=5))

    def setUp(self):
        self.version = 0
        self.saved = pagememo.memo
        pagememo.memo = Memo(version=lambda con: ("test", self.version))
        pagememo._shapes.clear()
        self.client.force_login(self.user)
        self.client.cookies["csrftoken"] = CSRF

    def tearDown(self):
        pagememo.memo = self.saved
        pagememo._shapes.clear()

    def changed(self):
        self.version += 1

    def get(self, url, **kw):
        r = self.client.get(url, **kw)
        return r, r.get("X-Pypen-Memo"), r.content.decode()

    def test_a_second_visit_is_kept_and_the_same(self):
        for url in ("/dashboard/", f"/pens/{self.pen.pk}/", "/stats/", "/api/pens", "/usages/add/"):
            r1, how1, body1 = self.get(url)
            if how1 == "skip":  # it read a header: the next one carries it in the key
                r1, how1, body1 = self.get(url)
            r2, how2, body2 = self.get(url)
            self.assertEqual((r1.status_code, r2.status_code), (200, 200), url)
            self.assertEqual((how1, how2), ("miss", "hit"), url)
            self.assertEqual(r1["Content-Type"], r2["Content-Type"])
            self.assertEqual(len(body1), len(body2), url)

    def test_a_kept_page_still_carries_the_headers_and_a_form_still_posts(self):
        self.get("/usages/add/")
        r, how, _ = self.get("/usages/add/")
        self.assertEqual(how, "hit")
        self.assertIn("Content-Security-Policy", r)
        self.assertIn("private", r["Cache-Control"])
        # The CSRF cookie is refreshed as a made page refreshes it.
        self.assertEqual(r.cookies["csrftoken"].value, CSRF)

    def test_a_commit_makes_the_page_again(self):
        self.get(f"/pens/{self.pen.pk}/")
        Pen.objects.filter(pk=self.pen.pk).update(model="M1000")
        _, how, body = self.get(f"/pens/{self.pen.pk}/")
        self.assertEqual(how, "hit")  # the swapped-in version did not move
        self.assertNotIn("M1000", body)
        self.changed()
        _, how, body = self.get(f"/pens/{self.pen.pk}/")
        self.assertEqual(how, "miss")
        self.assertIn("M1000", body)

    def test_a_new_day_makes_the_page_again(self):
        self.get("/dashboard/")
        key = next(iter(pagememo.memo._store))
        self.assertIn(date.today().isoformat(), key[2])

    def test_the_referer_is_in_the_key_of_a_page_that_reads_it(self):
        url = f"/usages/{self.usage.pk}/edit/"
        first = self.get(url, HTTP_REFERER="http://testserver/pens/?q=pel")[2]
        self.assertIn("/pens/?q=pel", first)
        for ref, want in (("/pens/?q=pel", "/pens/?q=pel"), ("/stats/", "/stats/"), ("/pens/?q=pel", "/pens/?q=pel")):
            _, how, body = self.get(url, HTTP_REFERER="http://testserver" + ref)
            self.assertIn(f'value="{want}"', body, ref)
        self.assertEqual(self.get(url, HTTP_REFERER="http://testserver/stats/")[1], "hit")

    def test_a_signed_out_session_is_never_served_a_kept_page(self):
        self.get("/dashboard/")
        self.assertEqual(self.get("/dashboard/")[1], "hit")
        self.client.logout()
        self.client.cookies["csrftoken"] = CSRF
        r, how, _ = self.get("/dashboard/")
        self.assertEqual(r.status_code, 302)
        self.assertIsNone(how)

    def test_what_is_never_kept(self):
        # No CSRF cookie: a kept form would carry a token for another secret.
        # No CSRF cookie and a page with a form: its token goes with the
        # cookie this answer sets.
        for _ in range(2):
            del self.client.cookies["csrftoken"]  # each answer sets it again
            self.assertEqual(self.get("/usages/add/")[1], "skip")
        self.client.cookies["csrftoken"] = CSRF
        # A flash message waiting in a cookie.
        self.client.cookies["messages"] = "x"
        self.assertIsNone(self.get("/dashboard/")[1])
        del self.client.cookies["messages"]
        # A 404, and paths that are never kept.
        self.get("/pens/999999/")
        self.assertEqual(self.get("/pens/999999/")[1], "skip")
        self.assertIsNone(self.get("/api/version")[1])
        # A POST is never answered from the store.
        self.get("/dashboard/")
        r = self.client.post(f"/usages/{self.usage.pk}/verdict/", {"verdict": "loved"})
        self.assertIsNone(r.get("X-Pypen-Memo"))

    def test_a_page_that_sets_a_cookie_is_not_kept(self):
        def view(request):
            from django.http import HttpResponse

            r = HttpResponse("hi")
            r.set_cookie("x", "1")
            return r

        mw = pagememo.PageMemo(view)
        from django.test import RequestFactory

        req = RequestFactory().get("/dashboard/")
        req.COOKIES = {"csrftoken": CSRF, "sessionid": "s"}

        class S(dict):
            session_key = "s"

        req.session = S(_auth_user_id="1")
        self.assertEqual(mw(req)["X-Pypen-Memo"], "skip")
        self.assertEqual(mw(req)["X-Pypen-Memo"], "skip")

    def test_a_page_without_a_form_is_kept_for_a_browser_without_a_csrf_cookie(self):
        # /pens/ carries no form, so it never sets the CSRF cookie: a browser
        # that opened only lists would never have had a kept page.
        del self.client.cookies["csrftoken"]
        hows = [self.get("/stats/")[1] for _ in range(3)]
        self.assertEqual(hows[-1], "hit")
        self.assertNotIn("csrftoken", self.client.cookies)

