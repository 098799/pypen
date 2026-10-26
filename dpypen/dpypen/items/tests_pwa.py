"""/sw.js is the kit's service worker (KIT-SW) with pypen's settings.

Navigations are network first and kept for offline now, so the one thing that
must hold is the old worker's reason for leaving them alone: the Google OAuth
hand-off. It lives under /accounts/, which the worker never touches.
"""

from django.test import Client, SimpleTestCase, override_settings
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
        self.assertEqual(s["files"], ["/static/"])
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
