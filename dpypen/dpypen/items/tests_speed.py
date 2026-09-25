"""Speed budgets for the pages people open most.

The dashboard is where every sign-in lands. It used to load every inking ever
made with its pen, ink, nib and both brands joined in, and prefetch every
pen's photos per row: ~3,900 model objects and ~190 ms of server time on bae
(2026-09-25), for a page that names about 30 of them. These tests pin the fix:
the objects the dashboard builds besides the light inking rows must not grow
with the history, and stay under a fixed cap.
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db.models.signals import post_init
from django.test import TestCase, override_settings

from dpypen.items.models import Brand, Ink, Nib, Pen, Rotation, Usage
from dpypen.items.tests import PLAIN_STATIC

# The inked-now rows (pen, pen brand, ink, ink brand, nib, photos), the
# rotation pens with their brands, and the two stat cards. Before the fix,
# 200 past inkings alone built over a thousand.
DASHBOARD_OBJECT_BUDGET = 60


@override_settings(STORAGES=PLAIN_STATIC)
class DashboardBudget(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("owner", password="x")
        rot = Rotation.objects.create(priority=1, how_often=30, whos="Tomek", in_use=True)
        cls.nib = Nib.objects.create(width="F", cut="Round", material="Gold")
        cls.pens, cls.inks = [], []
        for i in range(6):
            brand = Brand.objects.create(name=f"Brand {i}", nationality="Germany")
            cls.pens.append(
                Pen.objects.create(
                    obtained=date(2020, 1, 1),
                    brand=brand,
                    model=f"M{i}",
                    filling="Piston",
                    age="Modern",
                    obtained_from="shop",
                    out=False,
                    price=100,
                    rotation=rot,
                )
            )
            cls.inks.append(
                Ink.objects.create(
                    brand=brand, name=f"Ink {i}", color="Blue", obtained_from="shop", how="Bought", volume=50, rotation=rot, used_up=False
                )
            )
        for i in range(2):
            Usage.objects.create(pen=cls.pens[i], nib=cls.nib, ink=cls.inks[i], begin=date.today() - timedelta(days=3 + i))

    def setUp(self):
        self.client.force_login(self.user)

    def add_history(self, n):
        start = date.today() - timedelta(days=10 + 3 * n)
        Usage.objects.bulk_create(
            Usage(
                pen=self.pens[i % 6], nib=self.nib, ink=self.inks[i % 6], begin=start + timedelta(days=3 * i), end=start + timedelta(days=3 * i + 2)
            )
            for i in range(n)
        )

    def objects_built(self):
        """Model objects the dashboard builds, not counting the inking rows."""
        built = []

        def count(sender, **kwargs):
            if sender is not Usage:
                built.append(sender)

        post_init.connect(count, weak=False)
        try:
            r = self.client.get("/dashboard/")
        finally:
            post_init.disconnect(count)
        self.assertEqual(r.status_code, 200)
        return len(built)

    def test_objects_do_not_grow_with_history(self):
        self.add_history(40)
        small = self.objects_built()
        self.add_history(200)
        large = self.objects_built()
        self.assertEqual(small, large)
        self.assertLessEqual(large, DASHBOARD_OBJECT_BUDGET)

    def test_inked_now_still_shown_newest_first(self):
        self.add_history(40)
        html = self.client.get("/dashboard/").content.decode()
        self.assertIn("<strong>2</strong> inked", html)
        # pens[0] was inked a day after pens[1], so it leads.
        self.assertLess(html.index('<div class="ink">Brand 0 Ink 0</div>'),
                        html.index('<div class="ink">Brand 1 Ink 1</div>'))
