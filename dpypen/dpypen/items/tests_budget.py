"""Speed and size budgets from the speed pass of 11 Nov 2026 (AUDIT.md, "Speed pass").

Each test pins one gain, so a change that loses it fails here and not on a
phone a week later.
"""

import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

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
