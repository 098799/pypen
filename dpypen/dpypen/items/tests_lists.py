"""The lists by the kit's rules (kit README §14, PYPEN-7).

What §14 says a test must pin, for the pens, the inks, the inkings, /search/,
the palette and the JSON lists: a limit over 100 is refused (422), the default
page holds at most 50, the order is stable under ties (every id once across
the pages), the query count does not grow with the rows, "zur" finds "Zürich",
the highlighter escapes. And what this app keeps: the group headings
(priorities, colours) with their whole-group counts, never repeated by Load
more.
"""

import re
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from dpypen.items import lists
from dpypen.items.models import Brand, Ink, Nib, Pen, Rotation, Usage
from dpypen.items.templatetags.items_extras import highlight
from dpypen.items.tests import PLAIN_STATIC

MORE = {"HTTP_X_PYPEN_MORE": "1"}
LISTS = ["/pens/", "/inks/", "/usages/", "/search/?q=x", "/api/pens", "/api/inks", "/api/usages"]


def heads(html):
    return re.findall(r'class="group-head" data-more-head>\s*(?:<span class="dot"[^>]*></span>\s*)?<h3>([^<]+)</h3>', html)


def text(html):
    return re.sub(r"<[^>]+>", "", html)


def rows(html):
    return len(re.findall(r'<div class="list-row[^"]*" data-listnav-item', html))


class Collection(TestCase):
    """A small collection the tests grow as they need."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("owner", password="x")
        cls.brand = Brand.objects.create(name="Same", nationality="Germany")
        cls.rots = {n: Rotation.objects.create(priority=n, how_often=7 * (n + 1), whos="Tomek", in_use=True) for n in range(4)}
        cls.gone = Rotation.objects.create(priority=None, how_often=1, whos="Tomek", in_use=False)
        cls.nib = Nib.objects.create(width="F", cut="Round", material="Gold")

    def setUp(self):
        self.client.force_login(self.owner)

    def pens(self, n, rot=None, model="x", brand=None):
        Pen.objects.bulk_create(
            [
                Pen(
                    obtained=date(2020, 1, 1),
                    brand=brand or self.brand,
                    model=model,
                    filling="Piston",
                    age="Modern",
                    obtained_from="shop",
                    out=False,
                    price=10,
                    rotation=rot or self.rots[1],
                )
                for _ in range(n)
            ]
        )

    def inks(self, n, color="Blue", name="x", brand=None):
        Ink.objects.bulk_create(
            [
                Ink(
                    brand=brand or self.brand,
                    name=name,
                    color=color,
                    obtained_from="shop",
                    how="Bought",
                    volume=50,
                    rotation=self.rots[1],
                    used_up=False,
                )
                for _ in range(n)
            ]
        )

    def usages(self, n, end=True):
        if not Pen.objects.exists():
            self.pens(1)
        if not Ink.objects.exists():
            self.inks(1)
        pen, ink = Pen.objects.first(), Ink.objects.first()
        day = date(2024, 1, 1)
        Usage.objects.bulk_create([Usage(pen=pen, ink=ink, nib=self.nib, begin=day, end=day + timedelta(days=3) if end else None) for _ in range(n)])


@override_settings(STORAGES=PLAIN_STATIC)
class Paging(Collection):
    def test_a_limit_over_the_cap_is_refused(self):
        for url in LISTS:
            sep = "&" if "?" in url else "?"
            for bad in ("limit=1000", "limit=0", "offset=-1", "limit=many"):
                with self.subTest(url=url, bad=bad):
                    self.assertEqual(self.client.get(f"{url}{sep}{bad}").status_code, 422)

    def test_a_page_holds_fifty(self):
        self.pens(60)
        self.inks(60)
        self.usages(60)
        for url in ("/pens/", "/inks/", "/usages/"):
            with self.subTest(url=url):
                html = self.client.get(url).content.decode()
                self.assertEqual(rows(html), 50)
                self.assertIn("1–50 of 60", text(html))
                self.assertIn("offset=50", html)  # Load more
        for url in ("/api/pens", "/api/inks", "/api/usages"):
            with self.subTest(url=url):
                d = self.client.get(url).json()
                self.assertEqual(sorted(d), ["items", "limit", "offset", "total"])
                self.assertEqual((len(d["items"]), d["total"], d["limit"], d["offset"]), (50, 60, 50, 0))

    def test_every_row_once_across_the_pages(self):
        # Every pen, ink and inking ties on everything but the id.
        self.pens(23)
        self.inks(23)
        self.usages(23)
        for url in ("/api/pens", "/api/inks", "/api/usages"):
            with self.subTest(url=url):
                seen = []
                for offset in range(0, 30, 7):
                    seen += [i["id"] for i in self.client.get(f"{url}?limit=7&offset={offset}").json()["items"]]
                self.assertEqual(len(seen), 23)
                self.assertEqual(len(set(seen)), 23)

    def test_load_more_answers_the_next_rows_only(self):
        self.pens(60)
        html = self.client.get("/pens/?offset=50", **MORE).content.decode()
        self.assertNotIn("<html", html)
        self.assertEqual(rows(html), 10)
        self.assertNotIn("Load more", html)
        self.assertIn("X-Pypen-More", self.client.get("/pens/")["Vary"])

    def test_a_page_past_the_end_is_empty_not_an_error(self):
        self.pens(3)
        self.assertEqual(self.client.get("/pens/?offset=999999").status_code, 200)
        self.assertEqual(self.client.get("/api/pens?offset=999999").json()["items"], [])

    def test_a_guest_and_a_stranger(self):
        self.client.logout()
        self.assertEqual(self.client.get("/api/pens").status_code, 403)
        self.assertIn(self.client.post("/api/pens").status_code, (403, 405))


@override_settings(STORAGES=PLAIN_STATIC)
class QueryCount(Collection):
    def count(self, url):
        with CaptureQueriesContext(connection) as q:
            r = self.client.get(url)
        self.assertEqual(r.status_code, 200, url)
        return len(q)

    def test_flat_at_1_10_30_rows(self):
        urls = [
            "/pens/",
            "/pens/?view=grid",
            "/pens/?q=x",
            "/inks/",
            "/inks/?sort=inked",
            "/inks/?view=grid",
            "/usages/",
            "/usages/?q=x",
            "/search/?q=x",
            "/search/?q=x&sort=used",
            "/pub/inks/",
            "/api/pens",
            "/api/inks",
            "/api/usages",
            "/api/palette?q=x",
        ]
        seen = {u: [] for u in urls}
        made = 0
        for n in (1, 10, 30):
            self.pens(n - made)
            self.inks(n - made)
            self.usages(n - made)
            Usage.objects.filter(pk=Usage.objects.order_by("pk").first().pk).update(end=None)
            made = n
            for u in urls:
                seen[u].append(self.count(u))
        for u, counts in seen.items():
            with self.subTest(url=u, counts=counts):
                self.assertEqual(len(set(counts)), 1)


@override_settings(STORAGES=PLAIN_STATIC)
class Search(Collection):
    def test_zur_finds_zurich(self):
        zb = Brand.objects.create(name="Zürich Pens", nationality="Switzerland")
        self.pens(1, model="Limmat", brand=zb)
        self.inks(1, name="Zürichsee", color="Blue")
        self.usages(1)
        for url, word in (("/pens/?q=zur", "Zür"), ("/inks/?q=ZUR", "Zür"), ("/search/?q=zur", "Zür"), ("/usages/?q=zur", "Zür")):
            with self.subTest(url=url):
                html = self.client.get(url).content.decode()
                self.assertIn(f"<mark>{word}</mark>", html)
        self.assertEqual(self.client.get("/api/pens?q=zurich").json()["total"], 1)
        self.assertEqual(self.client.get("/api/inks?q=zurichsee").json()["total"], 1)
        pal = self.client.get("/api/palette?q=zur").json()["groups"]
        self.assertEqual([g["type"] for g in pal], ["pen", "ink"])

    def test_every_word_must_match_some_field(self):
        pilot = Brand.objects.create(name="Pilot", nationality="Japan")
        self.pens(1, model="Custom 74", brand=pilot)
        self.pens(1, model="Custom 823", brand=pilot)
        self.inks(1, name="Blue", brand=pilot)
        self.assertEqual(self.client.get("/api/pens?q=pilot 74").json()["total"], 1)
        self.assertEqual(self.client.get("/api/pens?q=pilot nothing").json()["total"], 0)
        # the palette took the whole query as one phrase before
        pal = self.client.get("/api/palette?q=pilot blue").json()["groups"]
        self.assertEqual([g["type"] for g in pal], ["ink"])

    def test_like_wildcards_are_plain_text(self):
        self.pens(3)
        self.assertEqual(self.client.get("/api/pens?q=%25").json()["total"], 0)
        self.assertEqual(self.client.get("/api/pens?q=_").json()["total"], 0)

    def test_the_highlighter_escapes(self):
        self.assertEqual(str(highlight("<b>Zürich</b>", "zur")), "&lt;b&gt;<mark>Zür</mark>ich&lt;/b&gt;")
        self.assertEqual(str(highlight("a<b", ["lt"])), "a&lt;b")
        self.pens(1, model="<script>x</script>")
        html = self.client.get("/pens/?q=script").content.decode()
        self.assertNotIn("<script>x", html)
        self.assertIn("&lt;<mark>script</mark>&gt;", html)

    def test_most_used_counts_the_inkings(self):
        # It summed the inkings' ids, so one late inking beat many early ones.
        b = Brand.objects.create(name="Kaweco", nationality="Germany")
        self.pens(1, model="Sport A", brand=b)
        self.pens(1, model="Sport B", brand=b)
        a, bb = Pen.objects.filter(brand=b).order_by("model")
        ink = Ink.objects.create(brand=b, name="Blue", color="Blue", obtained_from="s", how="Bought", volume=50, rotation=self.rots[1], used_up=False)
        for _ in range(3):
            Usage.objects.create(pen=a, ink=ink, nib=self.nib, begin=date(2020, 1, 1), end=date(2020, 2, 1))
        Usage.objects.bulk_create([Usage(id=9000, pen=bb, ink=ink, nib=self.nib, begin=date(2021, 1, 1), end=date(2021, 2, 1))])
        html = self.client.get("/search/?q=sport&type=pens&sort=used").content.decode()
        self.assertLess(html.index(f"/pens/{a.pk}/"), html.index(f"/pens/{bb.pk}/"))

    def test_both_kinds_preview_then_one_kind_goes_on(self):
        self.pens(25)
        html = self.client.get("/search/?q=x").content.decode()
        self.assertIn("1–20 of 25", text(html))
        nxt = re.search(r'href="([^"]*)" data-more', html).group(1).replace("&amp;", "&")
        self.assertIn("type=pens", nxt)
        self.assertIn("offset=20", nxt)
        more = self.client.get(nxt, **MORE).content.decode()
        self.assertEqual(rows(more), 5)


@override_settings(STORAGES=PLAIN_STATIC)
class Groups(Collection):
    def test_pen_headings_count_the_whole_group_and_continue(self):
        self.pens(30, rot=self.rots[0])
        self.pens(30, rot=self.rots[1])
        self.pens(5, rot=self.gone)
        first = self.client.get("/pens/").content.decode()
        self.assertEqual(heads(first), ["Priority 0", "Priority 1"])
        self.assertIn("30 pens · ~every 14 days", first)  # the group, not the 20 on this page
        more = self.client.get("/pens/?offset=50", **MORE).content.decode()
        # Priority 1 goes on from the last page: no second heading for it.
        self.assertEqual(heads(more), ["Defunct / sold"])
        self.assertIn('data-group="p1"', more)
        # A bookmarked page in the middle of a group does show its heading.
        page = self.client.get("/pens/?offset=50").content.decode()
        self.assertEqual(heads(page), ["Priority 1", "Defunct / sold"])

    def test_the_rotation_chips_filter_in_sql(self):
        self.pens(3, rot=self.rots[0])
        self.pens(2, rot=self.rots[2])
        other = Rotation.objects.create(priority=1, how_often=3, whos="Ozlem", in_use=True)
        self.pens(4, rot=other)
        d = self.client.get("/api/pens?rot=p2").json()
        self.assertEqual(d["total"], 2)
        self.assertEqual({i["group"] for i in self.client.get("/api/pens?rot=other").json()["items"]}, {"other"})
        self.assertEqual(self.client.get("/api/pens?rot=p9").json()["total"], 9)  # a stale chip: all
        html = self.client.get("/pens/").content.decode()
        for chip in ('data-navval="p0"', 'data-navval="p2"', 'data-navval="other"'):
            self.assertIn(chip, html)
        self.assertNotIn('data-navval="p1"', html)  # no pens, no chip
        # Ozlem's priority-1 pen sorts with the others, after Tomek's groups.
        groups = [i["group"] for i in self.client.get("/api/pens").json()["items"]]
        self.assertEqual(groups, ["p0"] * 3 + ["p2"] * 2 + ["other"] * 4)

    def test_ink_colour_headings_and_chip_counts_follow_the_search(self):
        self.inks(40, color="Black", name="Noir")
        self.inks(20, color="Blue", name="Bleu")
        self.inks(3, color="Blue", name="Noir")
        html = self.client.get("/inks/").content.decode()
        self.assertEqual(heads(html), ["Black", "Blue"])
        self.assertIn("23 bottles", html)
        more = self.client.get("/inks/?offset=50", **MORE).content.decode()
        self.assertEqual(heads(more), [])  # Blue goes on
        searched = self.client.get("/inks/?q=noir").content.decode()
        self.assertRegex(searched, r'cc-label">Blue</span>\s*<span class="cc-count">3<')
        self.assertEqual(self.client.get("/api/inks?q=noir&color=Blue").json()["total"], 3)

    def test_a_flat_sort_has_no_headings(self):
        self.inks(3, color="Black")
        self.inks(3, color="Blue")
        html = self.client.get("/inks/?sort=brand").content.decode()
        self.assertEqual(heads(html), [])

    def test_the_desk_stays_on_the_first_page(self):
        self.usages(3, end=False)
        self.usages(55)
        html = self.client.get("/usages/").content.decode()
        self.assertIn("3 on duty", html)
        self.assertEqual(rows(html), 50)
        more = self.client.get("/usages/?offset=50", **MORE).content.decode()
        self.assertNotIn("on duty", more)
        self.assertNotIn("Past <em>inkings</em>", more)
        self.assertEqual(rows(more), 5)


class KitWords(TestCase):
    def test_the_kits_fold_is_in_sql(self):
        with connection.cursor() as c:
            c.execute("SELECT fold(%s)", ["Zürich"])
            self.assertEqual(c.fetchone()[0], "zurich")
        self.assertEqual(lists.tokens(" a  b " + "c " * 20), ["a", "b"] + ["c"] * 6)
