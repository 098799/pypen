"""/sw.js is the kit's service worker (KIT-SW) with pypen's settings.

Navigations are network first and kept for offline now, so the one thing that
must hold is the old worker's reason for leaving them alone: the Google OAuth
hand-off. It lives under /accounts/, which the worker never touches.
"""

from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import resolve

from dpypen.items import pwa
from dpypen.items.tests import PLAIN_STATIC


@override_settings(STORAGES=PLAIN_STATIC)
class ServiceWorkerTests(SimpleTestCase):
    def test_sw_is_settings_then_the_kit(self):
        r = Client().get("/sw.js")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/javascript")
        self.assertEqual(r["Cache-Control"], "no-cache")
        body = r.content.decode()
        self.assertTrue(body.startswith("self.KITSW = {"))
        self.assertIn("/* KIT-SW: v1", body)
        self.assertNotIn("respondWith(fetch(event.request))", body)   # the old pass-through

    def test_settings(self):
        s = pwa.KITSW
        self.assertEqual((s["app"], s["where"], s["takeover"]), ("pypen", "internet", True))
        self.assertEqual(s["files"], ["/static/", "/kit/"])   # the kit's cached files too (kitshell.py)
        self.assertRegex(s["build"], r"^[0-9a-f]{12}$")
        self.assertEqual(s["build"], pwa._build())                    # content, not start time

    def test_the_oauth_hand_off_is_never_touched(self):
        """Every allauth route and LOGIN_URL is under a skipped prefix."""
        from django.conf import settings
        from allauth import urls as allauth_urls

        def walk(patterns, prefix=""):
            for p in patterns:
                route = prefix + str(p.pattern)
                if hasattr(p, "url_patterns"):
                    yield from walk(p.url_patterns, route)
                else:
                    yield route
        skip = pwa.KITSW["skip"]
        for route in walk(allauth_urls.urlpatterns, "/accounts/"):
            self.assertTrue(any(route.startswith(k) for k in skip), route)
        self.assertTrue(settings.LOGIN_URL.startswith("/accounts/"))
        self.assertEqual(resolve(settings.LOGIN_URL).route.split("/")[0], "accounts")

    def test_sign_out_forgets_the_kept_pages(self):
        from pathlib import Path
        html = (Path(pwa.__file__).parent / "templates/items/settings.html").read_text()
        self.assertIn("postMessage('KIT_FORGET')", html)


@override_settings(STORAGES=PLAIN_STATIC)
class OneName(TestCase):
    """Kit §4 Fleet UX "Names" (PYPEN-9): one name for the tile, short_name,
    the apple title, the offline page, the keys layer and the Install row;
    tab titles `‹page› · ‹app›`, and the home page is the name alone."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        cls.owner = get_user_model().objects.create_user("owner", password="x", is_superuser=True)

    def test_the_name(self):
        self.assertEqual(pwa.APP_NAME, "Grining Pens")
        self.assertLessEqual(len(pwa.APP_NAME), 12)  # a phone tile shows about 12 letters

    def test_manifest_and_worker(self):
        m = Client().get("/manifest.json").json()
        self.assertEqual((m["name"], m["short_name"]), (pwa.APP_NAME, pwa.APP_NAME))
        self.assertEqual(pwa.KITSW["name"], pwa.APP_NAME)
        self.assertIn('"name": "Grining Pens"', Client().get("/sw.js").content.decode())

    def test_every_screen_says_it_the_same_way(self):
        self.client.force_login(self.owner)
        home = self.client.get("/prev/dashboard/").content.decode()
        self.assertIn("<title>Grining Pens</title>", home)
        self.assertIn('<meta name="apple-mobile-web-app-title" content="Grining Pens">', home)
        self.assertIn("name: 'Grining Pens',", home)  # the keyboard layer
        self.assertIn('<span class="overline">Grining Pens</span>', home)
        self.assertIn("<title>Pens · Grining Pens</title>", self.client.get("/prev/pens/").content.decode())
        self.assertIn("<title>Settings · Grining Pens</title>", self.client.get("/prev/settings/").content.decode())
        for url in ("/prev/dashboard/", "/prev/pens/", "/prev/inks/", "/prev/usages/", "/prev/history/", "/prev/records/", "/prev/settings/"):
            html = self.client.get(url).content.decode()
            self.assertNotIn("Grining Fountain Pens", html, url)
            self.assertNotIn("the bureau'", html, url)

    def test_the_front_door(self):
        html = Client().get("/").content.decode()
        self.assertIn("<title>Grining Pens</title>", html)
        self.assertIn("Grining <em>Pens</em>", html)
