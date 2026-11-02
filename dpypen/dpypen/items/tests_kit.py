"""pypen against the kit (PYPEN-2, AUDIT.md "Kit adherence").

The pieces this pass took from ~/apps/kit, each pinned: the byte copies, the
new-version toast and its /api/version, pull to refresh, What's new and its
list API, the error pages in the app's chrome (JSON for a fetch), the PNG
icons and the bottom nav's sizes.
"""

import json
import re
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase, override_settings

from dpypen.items import error_pages, pwa
from dpypen.items.tests import PLAIN_STATIC

HERE = Path(__file__).resolve().parent
TPL = HERE / "templates" / "items"
KIT = Path("/home/tgrining/apps/kit")

# copy in pypen -> canonical file in the kit
COPIES = {
    TPL / "_pullrefresh.html": KIT / "snippets" / "pullrefresh.html",
    TPL / "_update.html": KIT / "snippets" / "update.html",
    TPL / "_whatsnew.html": KIT / "snippets" / "whatsnew.html",
    HERE / "errors.py": KIT / "py" / "errors.py",
    HERE / "whatsnew.py": KIT / "py" / "whatsnew.py",
    HERE / "lists.py": KIT / "py" / "lists.py",
}

NAVIGATE = {"HTTP_SEC_FETCH_MODE": "navigate", "HTTP_ACCEPT": "text/html"}


class TheCopiesAreTheKits(TestCase):
    def test_byte_for_byte(self):
        for copy, canon in COPIES.items():
            if canon.exists():  # the kit lives on p340; bae has only the copies
                self.assertEqual(copy.read_bytes(), canon.read_bytes(), copy.name)


@override_settings(STORAGES=PLAIN_STATIC)
class TheShellCarriesThem(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("owner", password="x")

    def test_owner_page(self):
        self.client.force_login(self.owner)
        html = self.client.get("/pens/").content.decode()
        self.assertEqual(html.count("<!-- KIT-UPDATE: v1"), 1)
        self.assertEqual(html.count("<!-- KIT-PULLREFRESH: v1"), 1)
        self.assertEqual(html.count("<!-- KIT-WHATSNEW: v2"), 1)
        # the toast compares this page's build with the server's
        self.assertIn('id: "%s"' % pwa.KITSW["build"], html)
        self.assertIn('url: "/api/version"', html)
        self.assertLess(html.index("window.KITUPDATE"), html.index("<!-- KIT-UPDATE"))
        self.assertLess(html.index("window.WHATSNEW"), html.index("<!-- KIT-WHATSNEW"))
        # the dot: on More (the tab bar), on the desk's menu button, on Settings in the menu
        self.assertGreaterEqual(html.count("data-whatsnew-dot"), 3)
        self.assertIn("u: '#whatsnew'", html)  # the palette entry
        self.assertNotIn("{#", html)

    def test_a_stranger_gets_no_log(self):
        # A stranger meets the shell only on an error page; it has no log.
        html = self.client.get("/no-such-page/", **NAVIGATE).content.decode()
        self.assertIn("<!-- KIT-PULLREFRESH", html)
        self.assertNotIn("<!-- KIT-WHATSNEW", html)
        self.assertNotIn("data-whatsnew-dot", html)

    def test_settings_opens_the_log(self):
        self.client.force_login(self.owner)
        html = self.client.get("/settings/").content.decode()
        self.assertIn("data-whatsnew-open", html)
        self.assertLess(html.index('<h2 class="kit-set-h">Look</h2>'), html.index('type="button" data-whatsnew-open>'))

    def test_the_walls_pull_too(self):
        self.client.force_login(self.owner)
        for url in ("/pub/pens/wall/", "/pub/inks/wall/"):
            html = self.client.get(url).content.decode()
            self.assertEqual(html.count("<!-- KIT-PULLREFRESH: v1"), 1, url)
            # the kit turns the browser's own pull off; none of the page's own
            self.assertNotIn("overscroll-behavior: none", html, url)


class TheBuildIsAsked(TestCase):
    def test_version_is_open_and_never_kept(self):
        r = Client().get("/api/version")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"build": pwa.KITSW["build"]})
        self.assertEqual(r["Cache-Control"], "no-store")


@override_settings(STORAGES=PLAIN_STATIC)
class WhatsNew(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("owner", password="x")

    def doc(self):
        return json.loads((HERE / "whatsnew.json").read_text())

    def test_the_file_reads(self):
        doc = self.doc()
        self.assertEqual(doc["app"], "pypen")
        ids = [e["id"] for e in doc["entries"]]
        self.assertEqual(len(ids), len(set(ids)))
        dates = [e["date"] for e in doc["entries"]]
        self.assertEqual(dates, sorted(dates, reverse=True), "newest entry on top")
        for e in doc["entries"]:
            self.assertTrue(e["title"] and e["use"], e["id"])
            for shot in e.get("shots", []):
                self.assertTrue(shot.startswith("/static/items/whatsnew/"), shot)
                f = HERE / "static" / shot.removeprefix("/static/")
                self.assertTrue(f.exists(), shot)
                self.assertLessEqual(f.stat().st_size, 150_000, shot)

    def test_every_tag_names_an_entry(self):
        ids = {e["id"] for e in self.doc()["entries"]}
        for f in TPL.rglob("*.html"):
            if f.name.startswith("_whatsnew"):
                continue
            for tag in re.findall(r'data-new(?:-seen)?="([^"]+)"', f.read_text()):
                self.assertIn(tag, ids, f.name)

    def test_the_list_api(self):
        self.assertEqual(self.client.get("/whatsnew.json").status_code, 302)  # a stranger
        self.client.force_login(self.owner)
        whole = self.client.get("/whatsnew.json").json()
        self.assertEqual(whole["entries"][0]["id"], self.doc()["entries"][0]["id"])
        page = self.client.get("/whatsnew.json?limit=1").json()
        self.assertEqual(len(page["items"]), 1)
        self.assertEqual(page["total"], len(self.doc()["entries"]))
        self.assertEqual(self.client.get("/whatsnew.json?limit=1000").status_code, 422)


@override_settings(STORAGES=PLAIN_STATIC, DEBUG=False)
class ErrorPages(TestCase):
    """Navigations get a page in the app's chrome with a way on; a fetch and
    /api/ get JSON (kit README §4 "404 / errors", §5.7)."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("owner", password="x")

    def test_a_missing_page_is_a_page_with_a_way_on(self):
        self.client.force_login(self.owner)
        r = self.client.get("/pens/no-such/", **NAVIGATE)
        self.assertEqual(r.status_code, 404)
        html = r.content.decode()
        self.assertIn('<main id="main">', html)
        self.assertIn('class="tabbar"', html)
        self.assertIn("Not here", html)
        self.assertIn('href="/dashboard/"', html)
        self.assertIn("<title>Not here · Grining Pens</title>", html)
        self.assertEqual(r["Cache-Control"], "no-store")
        self.assertEqual(r["X-Frame-Options"], "DENY")

    def test_a_missing_object_too(self):
        self.client.force_login(self.owner)
        r = self.client.get("/pens/987654/", **NAVIGATE)
        self.assertEqual(r.status_code, 404)
        self.assertIn("Not here", r.content.decode())

    def test_a_boosted_swap_gets_the_page(self):
        self.client.force_login(self.owner)
        r = self.client.get("/pens/987654/", HTTP_HX_REQUEST="true", HTTP_HX_BOOSTED="true", HTTP_SEC_FETCH_MODE="cors", HTTP_ACCEPT="*/*")
        self.assertEqual(r.status_code, 404)
        self.assertIn('<main id="main">', r.content.decode())

    def test_a_stranger_gets_the_front_page_way(self):
        html = self.client.get("/no-such-page/", **NAVIGATE).content.decode()
        self.assertIn('href="/"', html)
        self.assertNotIn('class="tabbar"', html)

    def test_a_fetch_and_the_api_get_json(self):
        self.client.force_login(self.owner)
        for url, headers in (("/pens/987654/", {"HTTP_SEC_FETCH_MODE": "cors"}), ("/api/nope", NAVIGATE), ("/static/items/nope.css", {})):
            r = self.client.get(url, **headers)
            self.assertEqual(r.status_code, 404, url)
            self.assertEqual(r["Content-Type"], "application/json", url)
            self.assertIn("detail", r.json(), url)

    def test_a_refused_form_says_what_to_do(self):
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.owner)
        r = c.post("/usages/add/", {}, **NAVIGATE)
        self.assertEqual(r.status_code, 403)
        html = r.content.decode()
        self.assertIn("That did not go through", html)
        self.assertIn("reload the page and send it again", html)

    def test_the_500_page_needs_nothing(self):
        req = RequestFactory().get("/pens/", **NAVIGATE)
        r = error_pages.server_error(req)
        self.assertEqual(r.status_code, 500)
        html = r.content.decode()
        self.assertIn("Something broke", html)
        self.assertNotIn("p340", html)
        self.assertIn('<main id="main">', html)  # an hx-boost swap selects it
        self.assertIn("location.reload()", html)
        self.assertEqual(r["Cache-Control"], "no-store")
        fetch = error_pages.server_error(RequestFactory().get("/pens/", HTTP_SEC_FETCH_MODE="cors"))
        self.assertEqual(fetch["Content-Type"], "application/json")

    def test_the_shell_swaps_an_error_page_in(self):
        self.client.force_login(self.owner)
        html = self.client.get("/pens/").content.decode()
        self.assertIn('document.addEventListener("htmx:beforeSwap"', html)


class Icons(TestCase):
    def test_the_manifest_names_committed_pngs(self):
        m = Client().get("/manifest.json").json()
        self.assertEqual(m["id"], "/")
        pngs = {(i["sizes"], i.get("purpose", "any")): i["src"] for i in m["icons"] if i["type"] == "image/png"}
        self.assertEqual(set(pngs), {("192x192", "any"), ("512x512", "any"), ("512x512", "maskable")})
        for src in pngs.values():
            name = re.sub(r"\.[0-9a-f]{12}\.png$", ".png", src).removeprefix("/static/")
            self.assertTrue((HERE / "static" / name).exists(), src)

    @override_settings(STORAGES=PLAIN_STATIC)
    def test_ios_gets_a_png(self):
        for url in ("/",):
            html = Client().get(url).content.decode()
            self.assertIn('rel="apple-touch-icon" href="/static/items/icons/apple-touch-icon.png"', html)


class BottomNav(TestCase):
    def test_kit_sizes(self):
        css = (HERE / "static" / "items" / "css" / "tabbar.css").read_text()
        self.assertIn("min-height: 56px;", css)
        self.assertIn("font-size: 11px;", css)


@override_settings(STORAGES=PLAIN_STATIC)
class InstallNudge(TestCase):
    """PYPEN-5, kit README §4 "Install": the kit's bar, for the owner and guests,
    never for a stranger."""

    @classmethod
    def setUpTestData(cls):
        from dpypen.items.models import InviteCode

        cls.owner = get_user_model().objects.create_user("owner", password="x")
        cls.invite = InviteCode.objects.create(token="nudge-token", label="friend")

    def test_owner_and_guest_get_one_bar(self):
        self.client.force_login(self.owner)
        guest = Client()
        guest.post(f"/i/{self.invite.token}/")
        for who, c in (("owner", self.client), ("guest", guest)):
            for url in ("/dashboard/", "/pens/", "/settings/"):
                html = c.get(url).content.decode()
                self.assertEqual(html.count("KIT-INSTALL: "), 1, (who, url))

    def test_a_stranger_never_meets_it(self):
        for url in ("/", "/no-such-page/", "/pub/pens/wall/", "/pub/inks/"):
            html = Client().get(url, **NAVIGATE).content.decode()
            self.assertNotIn("KIT-INSTALL", html, url)

    def test_the_bar_is_the_kits_byte_for_byte(self):
        copy = (TPL / "_install.html").read_bytes()
        self.assertIn(b"KIT-INSTALL", copy)
        canon = Path("/home/tgrining/apps/kit/snippets/install.html")
        if canon.exists():
            self.assertEqual(copy, canon.read_bytes())
        self.assertIn("days: 1", (TPL / "_installbar.html").read_text())   # no second-day rule: a guest may come once

    def test_settings_lets_the_bar_hand_the_offer_over(self):
        self.client.force_login(self.owner)
        html = self.client.get("/settings/").content.decode()
        self.assertIn("kitInstall.hand()", html)
        self.assertIn('data-kit-install="', html)
