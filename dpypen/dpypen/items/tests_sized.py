"""PYPEN-3: pictures at the size the page draws them, and the pieces two
pages used to paste (the share script, the samples strip, the back link).

sized.py makes a WebP copy with the kit's webp.py; the page draws the copy and
the viewer opens the stored file. Each test has its own MEDIA_ROOT, so the
dev media folder is never written.
"""

import io
import os
import re
import shutil
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import Client, override_settings
from django.urls import reverse
from PIL import Image

from dpypen.items import sized
from dpypen.items.models import PenPhoto
from dpypen.items.tests import PLAIN_STATIC
from dpypen.items.tests_doors import _Collection

HERE = Path(__file__).parent
TEMPLATES = HERE / "templates" / "items"
APP_CSS = HERE / "static" / "items" / "css" / "app.css"


def _photo(path: Path, size=(2400, 1800)):
    """A noisy JPEG of a stored photo's size (flat colour would compress to nothing)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.effect_noise(size, 60).convert("RGB")
    im.save(path, "JPEG", quality=85)


class _Media(_Collection):
    def setUp(self):
        self.media = tempfile.mkdtemp(prefix="pypen-sized-")
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        self.enterContext(override_settings(MEDIA_ROOT=self.media, STORAGES=PLAIN_STATIC))
        _photo(Path(self.media) / "pen_photos" / "a.jpg")
        _photo(Path(self.media) / "writing_samples" / "a.jpg", (1800, 1350))
        _photo(Path(self.media) / "ink_swatches" / "a.jpg", (1500, 1500))
        self.owner_client = Client()
        self.owner_client.force_login(self.owner)


class SizedCopies(_Media):
    def test_copy_is_webp_at_the_edge_and_smaller(self):
        photo = PenPhoto.objects.get(pk=self.photo.pk)
        url = sized.url(photo.image)
        self.assertEqual(url, "/media/sized/1200/pen_photos/a.webp")
        copy = Path(self.media) / "sized" / "1200" / "pen_photos" / "a.webp"
        with Image.open(copy) as im:
            self.assertEqual(im.format, "WEBP")
            self.assertEqual(max(im.size), 1200)
        self.assertLess(copy.stat().st_size, (Path(self.media) / "pen_photos" / "a.jpg").stat().st_size / 2)

    def test_a_missing_file_gives_the_stored_url(self):
        photo = PenPhoto.objects.get(pk=self.photo.pk)
        photo.image.name = "pen_photos/gone.jpg"
        self.assertEqual(sized.url(photo.image), "/media/pen_photos/gone.jpg")

    def test_no_field_no_url(self):
        self.assertIsNone(sized.url(None))

    def test_prune_removes_only_orphans(self):
        photo = PenPhoto.objects.get(pk=self.photo.pk)
        sized.url(photo.image)
        orphan = Path(self.media) / "sized" / "1200" / "pen_photos" / "deleted.webp"
        orphan.write_bytes(b"x")
        self.assertEqual(sized.prune(), 1)
        self.assertFalse(orphan.exists())
        self.assertTrue((Path(self.media) / "sized" / "1200" / "pen_photos" / "a.webp").exists())

    def test_the_deploy_command_makes_them_all(self):
        out = io.StringIO()
        call_command("sized_copies", stdout=out)
        self.assertIn("3 of 3 pictures drawn from a copy", out.getvalue())
        for rel in ("1200/pen_photos/a.webp", "1200/writing_samples/a.webp", "1200/ink_swatches/a.webp"):
            self.assertTrue((Path(self.media) / "sized" / rel).exists(), rel)


class PagesDrawTheCopy(_Media):
    def html(self, name, *args):
        r = self.owner_client.get(reverse(name, args=args))
        self.assertEqual(r.status_code, 200)
        return r.content.decode()

    def test_pen_page_draws_the_copy_and_the_viewer_opens_the_file(self):
        html = self.html("pens_detail", self.pen.pk)
        img = re.search(r'<img id="photoImg"[^>]*>', html).group(0)
        self.assertIn('src="/media/sized/1200/pen_photos/a.webp"', img)
        self.assertIn('data-zoom="/media/pen_photos/a.jpg"', img)

    def test_samples_and_swatches_draw_tiles(self):
        for name, args in (("pens_detail", [self.pen.pk]), ("inks_detail", [self.ink.pk])):
            html = self.html(name, *args)
            self.assertIn('src="/media/sized/1200/writing_samples/a.webp"', html, name)
            self.assertIn('data-zoom="/media/writing_samples/a.jpg"', html, name)
        html = self.html("inks_detail", self.ink.pk)
        self.assertIn('src="/media/sized/1200/ink_swatches/a.webp"', html)
        self.assertIn('data-zoom="/media/ink_swatches/a.jpg"', html)


@override_settings(STORAGES=PLAIN_STATIC)
class OneCopyOfEach(_Collection):
    """The share script, the samples strip and the back link live in one place."""

    def test_share_script_is_the_shells(self):
        for t in TEMPLATES.rglob("*.html"):
            self.assertNotIn("navigator.share", t.read_text(), t.name)
        c = Client()
        c.force_login(self.owner)
        for name, args in (("pens_detail", [self.pen.pk]), ("inks_detail", [self.ink.pk]), ("inks_list", [])):
            html = c.get(reverse(name, args=args)).content.decode()
            self.assertIn("items/js/share.js", html, name)
            self.assertIn("data-share-url=", html, name)

    def test_record_pages_carry_no_copy_of_the_shared_css(self):
        css = APP_CSS.read_text()
        for rule in (".samples-strip {", ".history-row {", ".back-link {", ".swatch-grid {"):
            self.assertIn(rule, css)
        for page in ("pens/detail.html", "inks/detail.html"):
            text = (TEMPLATES / page).read_text()
            for rule in (".samples-strip {", ".history-row {", "-back {"):
                self.assertNotIn(rule, text, f"{page} has its own {rule}")

    def test_no_back_link_is_left_unstyled(self):
        for t in TEMPLATES.rglob("*.html"):
            self.assertNotRegex(t.read_text(), r'class="(pen|ink)-back"', t.name)


@override_settings(STORAGES=PLAIN_STATIC)
class TheWallsShareOnePage(_Collection):
    def test_both_walls_extend_the_wall_page(self):
        for page in ("pens/wall.html", "inks/wall.html"):
            text = (TEMPLATES / page).read_text()
            self.assertTrue(text.startswith('{% extends "items/_wall.html" %}'), page)
            for own in (".wall-head {", ".theme-btn {", "kitTheme.set", "<html"):
                self.assertNotIn(own, text, f"{page} has its own {own}")

    def test_walls_get_the_kit_pieces(self):
        c = Client()
        c.force_login(self.owner)
        for name in ("share_pens_wall", "share_inks_wall"):
            r = c.get(reverse(name))
            self.assertEqual(r.status_code, 200, name)
            html = r.content.decode()
            for piece in ("items/css/wall.css", 'id="themeBtn"', '<script src="/kit/wall.js?v=',
                          '<link rel="stylesheet" href="/kit/wall.css?v=', "items/icons/apple-touch-icon.png", 'class="wall"'):
                self.assertIn(piece, html, f"{name}: {piece}")
        from dpypen.items import kitshell   # pull to refresh and New version are in wall.js
        for stamp in ("KIT-PULLREFRESH", "KIT-UPDATE"):
            self.assertIn(stamp, kitshell.KIT.files["wall.js"][0].decode())


class NoFixedInlineStyle(_Collection):
    """A style="" attribute holds only what the server knows per item (a
    colour, a width in %): a fixed look is a class in app.css (PYPEN-3)."""

    def test_templates(self):
        fixed = re.compile(r'style="[^"{]*"')
        for t in TEMPLATES.rglob("*.html"):
            if t.name in ("_keys.html", "_filters.html"):  # the kit's own markup (a header that shows it)
                continue
            self.assertEqual(fixed.findall(t.read_text()), [], t.relative_to(TEMPLATES))
