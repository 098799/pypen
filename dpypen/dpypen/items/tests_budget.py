"""Speed and size budgets from the speed pass of 11 Nov 2026 (AUDIT.md, "Speed pass").

Each test pins one gain, so a change that loses it fails here and not on a
phone a week later.
"""

import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase, TestCase

PROJECT = Path(__file__).resolve().parents[2]


class StartBudget(SimpleTestCase):
    """A worker that imports pandas, anthropic or google-genai at start pays
    ~0.6 s and ~80 MB for pages that never use them (P2 in AUDIT.md: 734 ms of
    imports before, 70 ms after). Only the old `supen` text page, a notebook
    upload and an AI photo need them, and they import them when called."""

    HEAVY = ("pandas", "anthropic", "google.genai")

    def test_the_app_starts_without_the_heavy_libraries(self):
        code = (
            "import os, sys, django;"
            "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dpypen.settings');"
            "django.setup();"
            "import dpypen.urls, dpypen.wsgi;"
            f"print(','.join(m for m in {self.HEAVY!r} if m in sys.modules))"
        )
        out = subprocess.run([sys.executable, "-c", code], cwd=PROJECT, capture_output=True, text=True, timeout=60, env={**os.environ})
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        self.assertEqual(out.stdout.strip(), "", "imported at start: " + out.stdout)


class InlineBudget(TestCase):
    """~92 KB of the same script and style went inline in every page (P3 in
    AUDIT.md): 75-90 % of a page's bytes, sent again on every tap. They are
    cached files now (kitshell.py: early.js, late.js, keys.css); what stays
    inline is per page (a chart's data, a config object, the accent)."""

    INLINE_MAX = 8 * 1024  # bytes of inline <script> and <style> code in one page (was ~92 KB)
    PAGES = ("/dashboard/", "/pens/", "/inks/", "/usages/", "/usages/add/", "/stats/timeline/", "/settings/",
             "/supen/", "/prev/dashboard/", "/prev/pens/")

    def test_pages_carry_no_shared_code_inline(self):
        import re
        from datetime import date

        from django.contrib.auth import get_user_model
        from django.test import Client, override_settings

        from dpypen.items.models import Brand, Pen, Rotation
        from dpypen.items.tests import PLAIN_STATIC

        user = get_user_model().objects.create_superuser("budget-owner", password="x")
        rot = Rotation.objects.create(priority=1, how_often=30, whos="Tomek", in_use=True)
        Pen.objects.create(obtained=date(2020, 1, 1), brand=Brand.objects.create(name="B", nationality="Japan"),
                           model="M", filling="Piston", age="Modern", obtained_from="shop", out=False, price=1, rotation=rot)
        c = Client()
        c.force_login(user)
        with override_settings(STORAGES=PLAIN_STATIC):
            for url in self.PAGES:
                html = c.get(url).content.decode()
                code = re.findall(r"<script>(.*?)</script>|<style>(.*?)</style>", html, re.S)
                size = sum(len(a) + len(b) for a, b in code)
                self.assertLess(size, self.INLINE_MAX, url)
                self.assertIn("/kit/late.js?v=", html, url)
