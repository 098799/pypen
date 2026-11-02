"""The empty, no-match and failed states by the kit (KIT-EMPTY, kit README §4
"Empty states", AUDIT.md pass 6).

Pinned: the byte copy is in every shell page once; each list's empty block is
the kit's markup with the right kind; every no-match has a way out; a
rotation chip with no pens is a no-match, not "no pens in the bureau"; an
empty cupboard is not "no inks match this filter"; the blocks that arrive by
an htmx swap are live regions; the shell turns a failed live search into the
kit's "could not load" block; and no own empty CSS is left.
"""

import re
from pathlib import Path

from django.test import override_settings

from dpypen.items.models import Ink, Pen
from dpypen.items.tests import PLAIN_STATIC
from dpypen.items.tests_lists import Collection

HERE = Path(__file__).resolve().parent
COPY = HERE / "templates" / "items" / "_empty.html"
CANON = Path("/home/tgrining/apps/kit/snippets/empty.html")
PARTIAL = {"HTTP_HX_REQUEST": "true"}


def blocks(html):
    """[(kind, the whole block)] for each kit block on the page (the snippet's
    own header comment shows the markup too: comments are left out)."""
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    return [(m.group(1), m.group(0)) for m in re.finditer(r'<div class="kit-empty[^"]*" data-kind="(\w+)"[^>]*>.*?</div>', html, re.S)]


@override_settings(STORAGES=PLAIN_STATIC)
class KitEmpty(Collection):
    def test_the_copy_is_the_kits(self):
        if CANON.exists():  # the kit lives on p340; bae has only the copy
            self.assertEqual(COPY.read_bytes(), CANON.read_bytes())

    def test_the_shell_carries_it_once(self):
        html = self.client.get("/pens/").content.decode()
        self.assertEqual(html.count("<!-- KIT-EMPTY: v1"), 1)
        # and the shared handler for a live search that fails
        self.assertIn('addEventListener("htmx:responseError", failed)', html)
        self.assertIn('addEventListener("htmx:sendError", failed)', html)
        self.assertIn("kitEmpty.fail(t,", html)

    def test_no_own_empty_css_is_left(self):
        css = (HERE / "static" / "items" / "css" / "app.css").read_text()
        self.assertNotRegex(css, r"\.empty\b")
        search = (HERE / "templates" / "items" / "search.html").read_text()
        self.assertNotIn("sr-empty", search)

    def test_no_pens_yet(self):
        got = blocks(self.client.get("/pens/").content.decode())
        self.assertEqual([k for k, _ in got], ["none"])
        self.assertIn("No pens in the bureau yet", got[0][1])

    def test_a_pen_search_with_no_match_can_be_cleared(self):
        self.pens(2)
        for view in ("", "&view=grid"):
            html = self.client.get(f"/pens/?q=zzz{view}", **PARTIAL).content.decode()
            ((kind, b),) = blocks(html)
            self.assertEqual(kind, "match")
            self.assertIn("No pen matches “zzz”", b)
            self.assertIn('role="status"', b)
            self.assertIn(">Clear the search</a>", b)
            self.assertNotIn("q=zzz", re.search(r'href="([^"]*)">Clear the search', b).group(1))

    def test_an_empty_rotation_chip_is_a_no_match_with_all_pens(self):
        self.pens(2, rot=self.rots[1])
        html = self.client.get("/pens/?rot=p3").content.decode()
        ((kind, b),) = blocks(html)
        self.assertEqual(kind, "match")
        self.assertIn("No pens in Priority 3", b)
        self.assertNotIn("bureau", b)
        self.assertIn('href="/pens/">All pens</a>', b)
        # the chip in force stays on show, at 0
        self.assertRegex(html, r'class="rotchip on"[^>]*data-navval="p3"[^>]*>3 <b>0</b>')

    def test_an_empty_cupboard_says_so(self):
        got = blocks(self.client.get("/inks/").content.decode())
        self.assertEqual([k for k, _ in got], ["none"])
        self.assertIn("No inks in the cupboard yet", got[0][1])
        self.assertNotIn("filter", got[0][1])

    def test_a_cupboard_of_samples_is_a_no_match_with_show_all(self):
        Ink.objects.create(brand=self.brand, name="s", color="Blue", obtained_from="x", how="Bought", volume=2, rotation=self.rots[1], used_up=False)
        ((kind, b),) = blocks(self.client.get("/inks/").content.decode())
        self.assertEqual(kind, "match")
        self.assertIn("Samples and used-up inks are hidden", b)
        self.assertIn("samples=1", b)
        self.assertIn("used=1", b)

    def test_an_ink_search_with_no_match_can_be_cleared(self):
        self.inks(2)
        for view in ("", "&view=grid"):
            html = self.client.get(f"/inks/?q=zzz{view}", **PARTIAL).content.decode()
            ((kind, b),) = blocks(html)
            self.assertEqual(kind, "match")
            self.assertIn("No ink matches “zzz”", b)
            self.assertIn('role="status"', b)
            self.assertIn(">Clear the search</a>", b)

    def test_inkings(self):
        html = self.client.get("/usages/").content.decode()
        self.assertEqual([k for k, _ in blocks(html)], ["none"])
        html = self.client.get("/usages/?q=zzz", **PARTIAL).content.decode()
        ((kind, b),) = blocks(html)
        self.assertEqual(kind, "match")
        self.assertIn(">Clear the search</a>", b)

    def test_search(self):
        html = self.client.get("/search/").content.decode()
        ((kind, b),) = blocks(html)
        self.assertEqual(kind, "none")
        self.assertIn("Type to search", b)
        self.pens(1)
        html = self.client.get("/search/?q=zzz&type=pens", **PARTIAL).content.decode()
        ((kind, b),) = blocks(html)
        self.assertEqual(kind, "match")
        self.assertIn('role="status"', b)
        clear = re.search(r'href="([^"]*)">Clear the search', b).group(1)
        self.assertNotIn("q=", clear)
        self.assertIn("type=pens", clear)
        self.assertIn(">Show the hidden ones</a>", b)
        # nothing hidden: no second way out
        html = self.client.get("/search/?q=zzz&type=pens&defunct=1", **PARTIAL).content.decode()
        self.assertNotIn("Show the hidden ones", html)

    def test_a_pen_never_inked(self):
        self.pens(1)
        html = self.client.get(f"/pens/{Pen.objects.get().pk}/").content.decode()
        got = [b for k, b in blocks(html) if k == "none"]
        self.assertTrue(any("kit-empty small" in b and "never been inked" in b for b in got), got)

    def test_every_pen_has_a_photo(self):
        html = self.client.get("/pens/needs-photos/").content.decode()
        self.assertTrue(any("Every pen in the collection has a photograph" in b for _, b in blocks(html)))
