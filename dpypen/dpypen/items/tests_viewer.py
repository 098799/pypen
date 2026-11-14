"""The picture viewer: the kit's (KIT-VIEWER, ~/apps/kit/snippets/viewer.html),
since consistency pass 15 (14 Nov 2026). It replaced pypen's own (PYPEN-1,
static/items/js/viewer.js + css/viewer.css, ~400 lines).

A pen's photos, an ink's swatches and the writing samples open full screen, to
be pinched and walked through. The kit file is a byte copy (_viewer.html),
bundled into /kit/shell.js and /kit/shell.css (kitshell.py), so both shells
carry it after the layer. It reads markup only: `data-view` (the file),
`data-view-group` (a set), `data-view-of` (a big photo that opens its
thumbs' set at the one marked aria-current or .active), `data-view-cap`,
`data-view-hi` (the stored file, fetched only when zoomed in). The behaviour is
walked in a real browser by tools/viewer_probe.py; these tests hold the markup.
"""

import re
from pathlib import Path

from django.test import Client, override_settings
from django.urls import reverse

from dpypen.items.models import PenPhoto
from dpypen.items.tests import PLAIN_STATIC, shipped
from dpypen.items.tests_doors import _Collection

HERE = Path(__file__).resolve().parent
COPY = HERE / "templates" / "items" / "_viewer.html"
CANON = Path("/home/tgrining/apps/kit/snippets/viewer.html")


def attrs(tag):
    return dict(re.findall(r'([\w-]+)="([^"]*)"', tag))



@override_settings(STORAGES=PLAIN_STATIC)
class PhotosOpenInTheKitViewer(_Collection):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        PenPhoto.objects.bulk_create(
            [
                PenPhoto(
                    pen=cls.pen,
                    image="pen_photos/b.jpg",
                    image_styled="pen_photos/b-styled.png",
                    styled_thumbnail="pen_photos/b-styled-thumb.webp",
                    kind="nib",
                    position=1,
                ),
            ]
        )
        PenPhoto.objects.bulk_create([PenPhoto(pen=cls.pen, image="pen_photos/c.jpg", review="check", position=2)])

    def setUp(self):
        self.owner_client = Client()
        self.owner_client.force_login(self.owner)
        self.guest = Client()
        self.guest.post(reverse("invite_activate", args=[self.invite.token]))

    def page(self, client, name, *args):
        r = client.get(reverse(name, args=args))
        self.assertEqual(r.status_code, 200, name)
        return r.content.decode()

    def assertSetsHold(self, html, where):
        """Every data-view-of names a set that is on the page, and every set
        member is a data-view (the photo check's group once had no members)."""
        groups = set(re.findall(r'data-view-group="([^"]+)"', html))
        for g in re.findall(r'data-view-of="([^"]+)"', html):
            self.assertIn(g, groups, f"{where}: data-view-of={g} has no set")
        for tag in re.findall(r"<(?:img|a)\b[^>]*data-view-group=[^>]*>", html):
            self.assertRegex(tag, r"\sdata-view[\s=>]", where)
        self.assertNotIn("data-zoom", html, f"{where}: the old viewer's markup")

    def test_the_copy_is_the_kits(self):
        if CANON.exists():  # the kit lives on p340; bae has only the copy
            self.assertEqual(COPY.read_bytes(), CANON.read_bytes())

    def test_both_shells_carry_the_kit_viewer_and_not_the_old_one(self):
        for name, args in (("pens_list", []), ("nx_pens_detail", [self.pen.pk])):
            html = shipped(self.owner_client, reverse(name, args=args))
            self.assertNotIn("items/js/viewer.js", html, name)
            self.assertNotIn("items/css/viewer.css", html, name)
            self.assertEqual(html.count("/*! KIT-VIEWER: v1."), 2, name)  # shell.css and shell.js
            self.assertIn("window.kitViewer", html, name)
            # after the layer: Back, Esc and focus come from kitLayer
            self.assertLess(html.index("/*! KIT-LAYER"), html.index("window.kitViewer"), name)
        self.assertFalse((HERE / "static" / "items" / "js" / "viewer.js").exists())
        self.assertFalse((HERE / "static" / "items" / "css" / "viewer.css").exists())

    def test_next_pen_photo_opens_the_thumbs_set_at_the_chosen_one(self):
        for client in (self.owner_client, self.guest):
            html = self.page(client, "nx_pens_detail", self.pen.pk)
            main = attrs(re.search(r'<img id="photoImg"[^>]*>', html).group(0))
            self.assertEqual(main["data-view-of"], "pen")
            self.assertRegex(main["data-view"], r"^/media/")
            self.assertNotIn("data-view-group", main)  # not a member: it opens at the thumb
            thumbs = [attrs(t) for t in re.findall(r"<a [^>]*data-thumb[^>]*>", html)]
            self.assertEqual(len(thumbs), 3)
            self.assertTrue(all(t["data-view-group"] == "pen" for t in thumbs))
            # the next UI marks the chosen thumb aria-current, which data-view-of honours
            self.assertEqual([t.get("aria-current") for t in thumbs], ["true", None, None])
            self.assertEqual(thumbs[1]["data-view-cap"], "Pelikan M800, nib close-up")
            self.assertEqual(thumbs[1]["href"], "/media/pen_photos/b-styled.png")  # a modified click opens the file
            # a thumb's link is its file: htmx must not boost it into #main
            self.assertIn('<div class="rec-thumbs" hx-boost="false">', html)
            self.assertSetsHold(html, "nx_pens_detail")

    def test_legacy_pen_photo_too(self):
        html = self.page(self.guest, "pens_detail", self.pen.pk)
        main = attrs(re.search(r'<img id="photoImg"[^>]*>', html).group(0))
        self.assertEqual(main["data-view-of"], "pen")
        thumbs = re.findall(r"<a [^>]*data-thumb[^>]*>", html)
        self.assertEqual(len(thumbs), 3)
        self.assertIn('class="active"', thumbs[0])
        self.assertIn("M800 · nib close-up", html)
        # the strip draws the small twin, not the full catalogue shot
        self.assertIn('src="/media/pen_photos/b-styled-thumb.webp"', html)
        self.assertIn('<div class="pen-photo-thumbs" hx-boost="false">', html)
        self.assertSetsHold(html, "pens_detail")

    def test_one_photo_opens_alone_with_its_caption(self):
        PenPhoto.objects.filter(pen=self.pen).exclude(pk=self.photo.pk).delete()
        for name in ("nx_pens_detail", "pens_detail"):
            html = self.page(self.guest, name, self.pen.pk)
            main = attrs(re.search(r'<img id="photoImg"[^>]*>', html).group(0))
            self.assertNotIn("data-view-of", main, name)
            self.assertEqual(main["data-view-cap"], "Pelikan M800", name)

    def test_shared_pen_page_too(self):
        html = self.page(self.guest, "share_pen", self.pen.share_token)
        self.assertIn('data-view-group="pen"', html)
        self.assertSetsHold(html, "share_pen")

    def test_samples_open_the_viewer_not_the_edit_form(self):
        for name, edit_name in (
            ("pens_detail", "usages_edit"),
            ("inks_detail", "usages_edit"),
            ("nx_pens_detail", "nx_usages_edit"),
            ("nx_inks_detail", "nx_usages_edit"),
        ):
            pk = self.ink.pk if "inks" in name else self.pen.pk
            edit = reverse(edit_name, args=[self.usage.pk])
            guest = self.page(self.guest, name, pk)
            self.assertNotIn("{#", guest, f"{name}: a template comment leaked into the page")
            self.assertIn('data-view-group="samples"', guest, name)
            self.assertNotIn(f'href="{edit}"', guest, f"{name}: a guest's sample links to the edit form")
            self.assertIn(f'href="{edit}"', self.page(self.owner_client, name, pk), name)
            self.assertSetsHold(guest, name)

    def test_swatches_open_the_viewer(self):
        for name in ("inks_detail", "nx_inks_detail"):
            self.assertIn('data-view-group="swatches"', self.page(self.guest, name, self.ink.pk), name)

    def test_owner_pages_mark_their_photos(self):
        o = self.owner_client
        for name, args, group in (
            ("inks_edit", [self.ink.pk], "swatches"),
            ("nx_inks_edit", [self.ink.pk], "swatches"),
            ("usages_edit", [self.usage.pk], "samples"),
            ("nx_usages_edit", [self.usage.pk], "samples"),
            ("pens_photo_edit", [self.pen.pk, self.photo.pk], "compare"),
            ("nx_pens_photo_edit", [self.pen.pk, self.photo.pk], "compare"),
        ):
            html = self.page(o, name, *args)
            self.assertIn(f'data-view-group="{group}"', html, name)
            self.assertSetsHold(html, name)

    def test_photo_check_is_one_set(self):
        # Its trigger named group "check" and its items "pen": the set was empty.
        html = self.page(self.owner_client, "nx_pens_photo_check")
        tags = re.findall(r"<img [^>]*data-view[^>]*>", html)
        self.assertEqual(len(tags), 1)
        self.assertEqual(attrs(tags[0])["data-view-group"], "check")
        self.assertSetsHold(html, "nx_pens_photo_check")

    def test_gantt_zoom_chips_are_not_pictures(self):
        # `data-zoom` named the Gantt's Fit/2×/4× chips too: a tap opened a
        # black viewer on "2". The viewer reads data-view only now.
        for name in ("history", "history_gantt"):
            html = self.page(self.owner_client, name)
            if 'id="ganttInner"' not in html:
                continue
            chips = re.findall(r'<button [^>]*data-zoom="\d"[^>]*>', html)
            self.assertEqual(len(chips), 3, name)
            for c in chips:
                self.assertNotIn("data-view", c, name)
            return
        self.fail("no page drew the Gantt")
