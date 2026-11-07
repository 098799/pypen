"""The kit's snippets as cached files (kitshell.py; shell.py is the byte copy
of ~/apps/kit/py/shell.py, kit README §5.9), not inline in every page.

Before (2026-11-07): the owner's /pens/ carried the snippets' style, script
and header comments again on each load; the 404 page a stranger meets was
193 KB."""

import gzip
import re
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from dpypen.items import kitshell
from dpypen.items.tests import PLAIN_STATIC

HERE = Path(__file__).resolve().parent
KIT = Path("/home/tgrining/apps/kit/py/shell.py")
NAVIGATE = {"HTTP_SEC_FETCH_MODE": "navigate", "HTTP_ACCEPT": "text/html"}
IMMUTABLE = "public, max-age=31536000, immutable"


def kit_urls(html):
    return re.findall(r'(?:src|href)="(/kit/[\w.]+\?v=[0-9a-f]+)"', html)


class TheModuleIsTheKits(TestCase):
    def test_byte_for_byte(self):
        copy = (HERE / "shell.py").read_bytes()
        self.assertIn(b"KIT-SHELL: v1", copy)
        if KIT.exists():  # the kit lives on p340; bae has only the copy
            self.assertEqual(copy, KIT.read_bytes())


@override_settings(STORAGES=PLAIN_STATIC)
class ThePagesAreLight(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("owner", password="x")

    def test_no_page_carries_a_snippet(self):
        self.client.force_login(self.owner)
        # Was 257 KB, 255 KB, 267 KB and 61 KB (the ink wall). What is left of a
        # shell page is mostly the keyboard layer (_keys.html, ~55 KB: Django
        # tags in it, so it stays inline).
        for url, budget in (("/pens/", 110_000), ("/next/pens/", 110_000), ("/settings/", 110_000),
                            ("/next/settings/", 110_000), ("/pub/pens/wall/", 10_000), ("/pub/inks/wall/", 10_000)):
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 200, url)
                html = r.content.decode()
                self.assertLess(len(r.content), budget, url)
                for stamp in ("KIT-LAYER", "KIT-TOAST", "KIT-EMPTY", "KIT-FILTERS", "KIT-UPDATE", "KIT-PULLREFRESH",
                              "KIT-WHATSNEW", "KIT-INSTALL", "KIT-SETTINGS", "KIT-THEME"):
                    self.assertNotIn(stamp, html, (url, stamp))

    def test_a_stranger_gets_light_pages_and_no_member_file(self):
        # Was 15 KB and 193 KB (the 404 in the shell; its keyboard layer stays inline).
        for url, budget, kw in (("/", 8_000, {}), ("/no-such-page/", 100_000, NAVIGATE)):
            with self.subTest(url=url):
                r = Client().get(url, **kw)
                self.assertLess(len(r.content), budget, url)
                self.assertNotIn("KIT-", r.content.decode())
                self.assertNotIn("/kit/member.", r.content.decode())


@override_settings(STORAGES=PLAIN_STATIC)
class TheFilesAreKept(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("owner", password="x")

    def test_each_file_a_page_links_is_immutable_gzipped_and_answers_304(self):
        self.client.force_login(self.owner)
        urls = set()
        for page in ("/pens/", "/next/pens/", "/pub/inks/wall/"):
            urls |= set(kit_urls(self.client.get(page).content.decode()))
        names = sorted(u.split("?")[0].removeprefix("/kit/") for u in urls)
        self.assertEqual(names, sorted(kitshell.KIT.files))
        stranger = Client()   # code, no data: anyone may fetch it
        for url in urls:
            with self.subTest(url=url):
                r = stranger.get(url, HTTP_ACCEPT_ENCODING="gzip")
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r["Cache-Control"], IMMUTABLE)
                self.assertEqual(r["Content-Encoding"], "gzip")
                self.assertIn(b"KIT-", gzip.decompress(r.content))
                self.assertTrue(r["Content-Type"].startswith(("text/css", "text/javascript")))
                self.assertIn("Content-Security-Policy", r.headers)   # pypen's headers on every answer
                self.assertEqual(r["X-Frame-Options"], "DENY")
                again = stranger.get(url, HTTP_IF_NONE_MATCH=r["ETag"])
                self.assertEqual(again.status_code, 304)
                self.assertEqual(again.content, b"")
                self.assertEqual(stranger.head(url).status_code, 200)
                # a page from before a deploy names an old version: never pinned
                self.assertEqual(stranger.get(url.split("?")[0] + "?v=old")["Cache-Control"], "no-cache")

    def test_unknown_names_and_writes_are_refused(self):
        self.assertEqual(Client().get("/kit/nope.js").status_code, 404)
        self.assertEqual(Client().get("/kit/_toast.html").status_code, 404)
        self.assertNotEqual(Client().post("/kit/shell.js").status_code, 200)

    def test_the_shells_keep_the_order_the_snippets_had(self):
        js = kitshell.KIT.files["shell.js"][0].decode()
        at = [js.index(f"/*! {n}:") for n in ("KIT-LAYER", "KIT-TOAST", "KIT-EMPTY", "KIT-FILTERS", "KIT-UPDATE", "KIT-PULLREFRESH")]
        self.assertEqual(at, sorted(at))
        self.assertEqual(at[0], 0)
        self.client.force_login(self.owner)
        for page in ("/pens/", "/next/pens/"):
            html = self.client.get(page).content.decode()
            # blocking at the top of <body>, before the shells' own scripts that call them
            body = html[html.index("<body"):]
            self.assertLess(body.index("window.KITUPDATE"), body.index('<script src="/kit/shell.js'))
            self.assertLess(body.index('<script src="/kit/shell.js'), body.index('<script src="/kit/member.js'))
            self.assertLess(body.index('<script src="/kit/member.js'), body.index("window.__kitMsgs"))
            self.assertIn('<link rel="stylesheet" href="/kit/shell.css', html.split("</head>")[0])
