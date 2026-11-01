"""The photo viewer (PYPEN-1): a pen's photos, an ink's swatches and the
writing samples open full screen, to be pinched and walked through.

The behaviour lives in static/items/js/viewer.js and is walked in a real
browser by tools/viewer_probe.py; these tests hold the markup it reads: every
page with photos marks them, the shell loads the script, and a guest's tap on a
writing sample no longer lands on the sign-in page of the edit form.
"""

from pathlib import Path

from django.test import Client, override_settings
from django.urls import reverse

from dpypen.items.models import PenPhoto
from dpypen.items.tests import PLAIN_STATIC
from dpypen.items.tests_doors import _Collection

VIEWER_JS = Path(__file__).parent / "static" / "items" / "js" / "viewer.js"


@override_settings(STORAGES=PLAIN_STATIC)
class PhotosOpenInTheViewer(_Collection):
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

    def setUp(self):
        self.owner_client = Client()
        self.owner_client.force_login(self.owner)
        self.guest = Client()
        self.guest.post(reverse("invite_activate", args=[self.invite.token]))

    def page(self, client, name, *args):
        r = client.get(reverse(name, args=args))
        self.assertEqual(r.status_code, 200, name)
        return r.content.decode()

    def test_the_shell_loads_the_viewer(self):
        html = self.page(self.owner_client, "pens_list")
        self.assertIn("items/js/viewer.js", html)

    def test_pen_photo_opens_its_group(self):
        for client in (self.owner_client, self.guest):
            html = self.page(client, "pens_detail", self.pen.pk)
            self.assertIn('id="photoImg"', html)
            # the viewer opens the stored file, whatever size the page draws (PYPEN-3)
            self.assertRegex(html, r'id="photoImg"[^>]*data-zoom="/media/[^"]+" data-zoom-group="pen"')
            # two photos: each thumb is an item of the group, with its full file
            self.assertEqual(html.count('data-zoom-item="pen"'), 2)
            self.assertIn('data-zoom-src="/media/pen_photos/b-styled.png"', html)
            self.assertIn("M800 · nib close-up", html)
            # the strip draws the small twin, not the full catalogue shot
            self.assertIn('src="/media/pen_photos/b-styled-thumb.webp"', html)

    def test_shared_pen_page_too(self):
        html = self.page(self.guest, "share_pen", self.pen.share_token)
        self.assertIn('data-zoom-group="pen"', html)

    def test_samples_open_the_viewer_not_the_edit_form(self):
        edit = reverse("usages_edit", args=[self.usage.pk])
        for name, args in (("pens_detail", [self.pen.pk]), ("inks_detail", [self.ink.pk])):
            guest = self.page(self.guest, name, *args)
            self.assertNotIn("{#", guest, f"{name}: a template comment leaked into the page")
            self.assertIn('data-zoom-item="samples"', guest)
            self.assertNotIn(f'href="{edit}"', guest, f"{name}: a guest's sample links to the edit form")
            owner = self.page(self.owner_client, name, *args)
            self.assertIn(f'class="sc-edit" href="{edit}"', owner)

    def test_swatches_open_the_viewer(self):
        html = self.page(self.guest, "inks_detail", self.ink.pk)
        self.assertIn('data-zoom-item="swatches"', html)

    def test_owner_pages_mark_their_photos(self):
        self.assertIn('data-zoom-item="swatches"', self.page(self.owner_client, "inks_edit", self.ink.pk))
        self.assertIn('data-zoom-item="samples"', self.page(self.owner_client, "usages_edit", self.usage.pk))
        self.assertIn('data-zoom-item="compare"', self.page(self.owner_client, "pens_photo_edit", self.pen.pk, self.photo.pk))

    def test_viewer_is_a_kit_layer(self):
        js = VIEWER_JS.read_text()
        # Back, Esc and the lock come from the kit, never its own history code
        self.assertIn("kitLayer.open(dlg", js)
        self.assertIn("kitLayer.close(dlg)", js)
        for own in ("pushState", "popstate", "history.back"):
            self.assertNotIn(own, js)
