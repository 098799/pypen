"""The kit's list controls in pypen (kit README §4 "Filters and search", AUDIT pass 7).
What htmx does with them is walked in a browser: tools/filters_probe.py."""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from dpypen.items.models import Brand, Ink, Nib, Pen, Rotation, Usage
from dpypen.items.tests import PLAIN_STATIC


@override_settings(STORAGES=PLAIN_STATIC)
class KitControls(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("owner", password="x")
        b = Brand.objects.create(name="Pilot")
        rot = Rotation.objects.create(priority=1, how_often=7, whos="Tomek", in_use=True)
        Ink.objects.create(brand=b, name="Asa-gao", color="Blue", obtained_from="s", how="Bought", volume=50, rotation=rot, used_up=False)

    def setUp(self):
        self.client.force_login(self.owner)

    def page(self, url):
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200, url)
        return r.content.decode()

    def test_the_old_controls_are_gone(self):
        for url in ("/prev/inks/", "/prev/pens/", "/prev/usages/", "/prev/search/", "/prev/history/gantt/"):
            html = self.page(url)
            self.assertIn('<script src="/kit/shell.js', html, url)   # KIT-FILTERS is in it (kitshell.py)
            for old in ('class="fb-toggle', 'class="cc', 'class="rotchip', 'class="seg-pill', 'class="toggle-check',
                        'class="sort-select', 'hx-push-url="true"', 'role="tab"', 'delay:200ms'):
                self.assertNotIn(old, html.split("<main", 1)[1], (url, old))

    def test_inks_chips_say_what_is_on(self):
        html = self.page("/prev/inks/?color=Blue")
        self.assertRegex(html, r'class="kit-chip" data-color aria-current="true"[^>]*>\s*<i class="kit-chip-dot"[^>]*></i>Blue <b>1</b>')
        self.assertIn('class="kit-chip kit-chip-clear"', html)
        self.assertNotIn("kit-chip-clear", self.page("/prev/inks/").split("<main", 1)[1])
        self.assertIn('hx-sync="#inkFilterForm:replace"', html)

    def test_an_unknown_value_is_no_filter(self):
        html = self.page("/prev/inks/?color=zzz&sort=zzz")
        self.assertNotIn('data-color aria-current', html)
        self.assertRegex(html, r'<option value="" selected>')
        html = self.page("/prev/pens/?rot=zzz")
        self.assertRegex(html, r'class="kit-chip" aria-current="true"\s+data-navkey="rot" data-navval=""')
        html = self.page("/prev/search/?type=zzz&sort=zzz")
        self.assertIn('aria-current="true"><input type="radio" form="searchForm" name="type" value="both"', html)
        self.assertRegex(html, r'<option value="alpha" selected>')

    def test_every_box_has_a_label_and_replaces(self):
        for url, label in (("/prev/inks/", "Search inks"), ("/prev/pens/", "Search pens"), ("/prev/usages/", "Search inkings"),
                           ("/prev/search/", "Search pens and inks")):
            main = self.page(url).split("<main", 1)[1]
            self.assertIn(f'aria-label="{label}"', main, url)
            self.assertIn('class="kit-search', main, url)
            self.assertIn("delay:300ms", main, url)
            self.assertIn('hx-replace-url="true"', main, url)

    def test_the_menu_search_waits_for_enter(self):
        html = self.page("/prev/pens/")
        self.assertIn('aria-label="Search pens and inks"', html)
        menu = html.split('id="menuSearchForm"')[1].split("</script>")[0]
        self.assertNotIn("setTimeout", menu)
        self.assertIn('"submit"', menu)

    def test_the_gantt_rotation_is_in_the_address(self):
        # The chips stand with the chart, so it needs one inked pen.
        b, rot, ink = Brand.objects.get(), Rotation.objects.get(), Ink.objects.get()
        pen = Pen.objects.create(obtained=date(2020, 1, 1), brand=b, model="74", filling="Piston", age="Modern", obtained_from="s", out=False, price=1, rotation=rot)
        Usage.objects.create(pen=pen, ink=ink, nib=Nib.objects.create(width="F", cut="Round", material="Gold"), begin=date(2020, 1, 1))
        html = self.page("/prev/history/gantt/?rot=p1")
        self.assertRegex(html, r'data-rot="p1" aria-pressed="true"')
        self.assertIn('showRot("p1")', html)
        html = self.page("/prev/history/gantt/?rot=zzz")
        self.assertRegex(html, r'data-rot="" aria-pressed="true"')
        self.assertIn('showRot("")', html)

    def test_the_public_cupboard_and_wall_have_them(self):
        self.client.logout()
        with self.settings(PUBLIC_SHOWCASE=True):
            html = self.page("/pub/inks/")
            wall = self.page("/pub/inks/wall/")
        self.assertIn('class="kit-search', html)
        self.assertIn('id="inkFilters"', html)
        self.assertRegex(wall, r'class="kit-chip" href="/pub/inks/wall/\?samples=0" aria-current="true"')
        self.assertIn('<script src="/kit/wall.js', wall)   # KIT-FILTERS is in it (kitshell.py)
        from dpypen.items import kitshell
        self.assertIn("/*! KIT-FILTERS: v1", kitshell.KIT.files["wall.js"][0].decode())
