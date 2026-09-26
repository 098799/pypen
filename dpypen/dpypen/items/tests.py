"""Every page that carries the keyboard layer must render.

_keys.html is a copy of ~/apps/kit/snippets/keys.html and is mostly JavaScript.
Django's template engine reads `{{`, `{%` and `{#` wherever they are, so a new
copy of the layer can break every page at once. These tests render each page
that extends the shell (the shell includes the layer) and check the layer is
there and is the version we think it is.
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.template.loader import get_template
from django.test import TestCase, override_settings

from dpypen.items.models import Brand, Ink, Nib, Pen, Rotation, Usage

PLAIN_STATIC = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=PLAIN_STATIC)
class KeysLayerRenders(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("owner", password="x")
        brand = Brand.objects.create(name="Pelikan", nationality="Germany")
        rot = Rotation.objects.create(priority=1, how_often=1, whos="T", in_use=True)
        cls.pen = Pen.objects.create(
            obtained=date(2020, 1, 1), brand=brand, model="M800", filling="Piston",
            age="Modern", obtained_from="shop", out=False, price=100, rotation=rot)
        cls.ink = Ink.objects.create(
            brand=brand, name="4001 Blue", color="Blue", obtained_from="shop",
            how="Bought", volume=50, rotation=rot, used_up=False)
        nib = Nib.objects.create(width="F", cut="Round", material="Gold")
        Usage.objects.create(pen=cls.pen, nib=nib, ink=cls.ink,
                             begin=date.today() - timedelta(days=30),
                             end=date.today() - timedelta(days=10))
        Usage.objects.create(pen=cls.pen, nib=nib, ink=cls.ink,
                             begin=date.today() - timedelta(days=5))

    def setUp(self):
        self.client.force_login(self.user)

    def pages(self):
        return [
            "/dashboard/", "/history/", "/history/calendar/", "/history/gantt/",
            "/history/matrix/", "/records/", "/search/", "/search/?q=pelikan",
            "/settings/", "/usages/", "/usages/add/", "/pens/", "/pens/?view=grid",
            "/pens/add/", "/pens/needs-photos/", f"/pens/{self.pen.pk}/",
            f"/pens/{self.pen.pk}/edit/", "/inks/", "/inks/?view=grid", "/inks/add/",
            f"/inks/{self.ink.pk}/", f"/inks/{self.ink.pk}/edit/", "/import/",
            "/next/", f"/next/?pen={self.pen.pk}",
        ]

    def test_the_layer_template_compiles(self):
        html = get_template("items/_keys.html").render({})
        self.assertIn("window.__keysLoaded", html)
        self.assertNotIn("endcomment", html)
        self.assertNotIn("KEYS v1", html)      # the header is a comment, not output

    def test_every_page_with_the_layer_renders(self):
        for url in self.pages():
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 200, url)
                html = r.content.decode()
                self.assertIn('id="kwk"', html)             # which-key: the v1 layer
                self.assertIn("__keysPageKey", html)        # the page hook
                self.assertIn("window.__keysList", html)    # the shell names the list
                self.assertNotIn("dotfiles/webkit", html)

    def test_palette_answers_in_groups(self):
        d = self.client.get("/api/palette?q=pelikan").json()
        self.assertEqual([g["type"] for g in d["groups"]], ["pen", "ink"])
        self.assertEqual(d["groups"][0]["items"][0]["u"], f"/pens/{self.pen.pk}/")
        self.assertEqual(self.client.get("/api/palette?q=").json(), {"groups": []})

    def test_palette_is_closed_to_strangers(self):
        self.client.logout()
        self.assertEqual(self.client.get("/api/palette?q=a").status_code, 403)
