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


class SameAnswersFaster(SimpleTestCase):
    """The rewrites of the speed pass give what the code before them gave."""

    def test_peak_day_is_the_old_count_per_pen_day(self):
        import random
        from collections import Counter
        from datetime import date, timedelta
        from types import SimpleNamespace as N

        from dpypen.items.records import _peak_day

        def old(usages, today):  # records.py before P7, verbatim
            day_counts = Counter()
            for u in usages:
                end = u.end or today
                cur = u.begin
                while cur <= end:
                    day_counts[cur] += 1
                    cur += timedelta(days=1)
                    if (cur - u.begin).days > 2000:
                        break
            return day_counts.most_common(1)[0] if day_counts else None

        rnd = random.Random(11)
        base = date(2020, 1, 1)
        for _ in range(1500):
            us = []
            for _ in range(rnd.randint(0, 10)):
                s = base + timedelta(days=rnd.randint(0, 40))
                e = None if rnd.random() < 0.2 else s + timedelta(days=rnd.randint(-3, 30))
                us.append(N(begin=s, end=e))
            if rnd.random() < 0.1:  # a fill longer than the cap
                us.append(N(begin=base, end=base + timedelta(days=2100)))
            today = base + timedelta(days=rnd.randint(0, 2200))
            self.assertEqual(_peak_day(us, today), old(us, today), (us, today))

    def test_timeline_bars_are_the_old_template_markup(self):
        from datetime import date

        from django.template import Context, Template

        from dpypen.items.history import _bars_html

        bars = [
            {"left": 1.25, "width": 0.2, "bg": "linear-gradient(90deg, #123 0%, #456 100%)", "ink": "Pelikan <4001> & Co",
             "ink_id": 7, "nib": 'F "steel"', "begin": date(2021, 9, 5), "end": date(2021, 9, 6), "days": 1, "current": False},
            {"left": 98.5, "width": 1.5, "bg": "#000", "ink": "Iroshizuku Kon-peki", "ink_id": 12, "nib": "M gold",
             "begin": date(2026, 1, 31), "end": None, "days": 0, "current": True},
        ]
        old = Template(  # next/stats/timeline.html before P6
            "{% load l10n %}{% for b in bars %}<button type=\"button\" class=\"{% if b.current %}is-now{% endif %}\" style=\"left: {{ b.left|unlocalize }}%; width: {{ b.width|unlocalize }}%; --sw: {{ b.bg }}\" data-tip-title=\"{{ b.begin|date:'j M Y' }} to {% if b.end %}{{ b.end|date:'j M Y' }}{% else %}now{% endif %}\" data-tip-lead=\"{{ b.ink }}\" data-tip=\"{{ b.nib }}, {{ b.days }} day{{ b.days|pluralize }}\" data-tip-links=\"Open the ink|{% url 'nx_inks_detail' b.ink_id %}\" aria-label=\"{{ b.ink }}, {{ b.days }} days\"></button>{% endfor %}"
        ).render(Context({"bars": bars}))
        self.assertEqual(_bars_html(bars), old)
