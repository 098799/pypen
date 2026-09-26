"""Every admin list page renders, found broken on the bugs pass of 2026-09-26.

django-money patches Django's `display_for_field` so a MoneyField shows as
"100.00 zł". Up to 3.5.3 the patch took exactly three arguments; Django 6.0's
changelist passes a fourth, `avoid_link=`, so every list page in /admin/ raised
TypeError and answered 500 — for every model with a row, money or not. 3.6.1
forwards the extra arguments.
"""

from datetime import date, timedelta

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from dpypen.items.models import Brand, Ink, Nib, Pen, Rotation, Usage


class AdminListsRender(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser("owner", "owner@example.com", "x")
        brand = Brand.objects.create(name="Pelikan", nationality="Germany")
        rot = Rotation.objects.create(priority=1, how_often=1, whos="T", in_use=True)
        pen = Pen.objects.create(
            obtained=date(2020, 1, 1),
            brand=brand,
            model="M800",
            filling="Piston",
            age="Modern",
            obtained_from="shop",
            out=False,
            price=100,
            rotation=rot,
        )
        ink = Ink.objects.create(
            brand=brand, name="4001 Blue", color="Blue", obtained_from="shop", how="Bought", volume=50, rotation=rot, used_up=False, price=20
        )
        nib = Nib.objects.create(width="F", cut="Round", material="Gold")
        Usage.objects.create(pen=pen, nib=nib, ink=ink, begin=date.today() - timedelta(days=5))

    def setUp(self):
        self.client.force_login(self.user)

    def test_every_changelist(self):
        broken = []
        for model in admin.site._registry:
            url = reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist")
            try:
                status = self.client.get(url).status_code
            except Exception as e:
                status = repr(e)
            if status != 200:
                broken.append(f"{url}: {status}")
        self.assertEqual(broken, [])

    def test_money_still_shows_as_money(self):
        response = self.client.get(reverse("admin:items_pen_changelist"))
        self.assertContains(response, "100.00")
