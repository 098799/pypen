"""Findings from the security pass of 2026-09-25, each pinned by a test.

The site's one way in is Google, and only for the addresses in ALLOWED_EMAILS
(dpypen.items.auth.AllowlistAdapter). These tests keep the other doors shut.
"""

import re
from importlib.metadata import PackageNotFoundError, version

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase


class AdminHasNoPasswordDoor(TestCase):
    """/admin/ used to take a username and password.

    That skipped the allowlist: the database still holds an `admin` superuser
    with a usable password from before Google sign-in, and the form was open
    to the internet with only nginx's rate limit in front of it. The admin
    login now sends a stranger to Google, like every other page.
    """

    @classmethod
    def setUpTestData(cls):
        get_user_model().objects.create_superuser("admin", "admin@example.com", "correct horse")

    def test_the_login_page_sends_a_stranger_to_google(self):
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(settings.LOGIN_URL))

    def test_a_right_password_does_not_sign_in(self):
        response = self.client.post("/admin/login/", {"username": "admin", "password": "correct horse", "next": "/admin/"})
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(response["Location"].startswith(settings.LOGIN_URL))

    def test_the_admin_itself_is_still_closed(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)


# The first release with no known advisory, as pip-audit saw bae's venv on
# 2026-09-25. Only what the running site imports or parses input with; the dev
# tools in the same venv (black, pytest, click, pygments, setuptools) never see
# a request. requirements.txt pins these; the test keeps an old venv from
# passing for a new one.
SECURITY_FLOORS = {
    "Django": "6.0.8",  # 11 advisories in 6.0.4, among them session and cache header leaks
    "pillow": "12.3.0",  # heap overflows in decoders; every upload goes through Image.open
    "djangorestframework": "3.17.2",
    "sqlparse": "0.6.0",
    "PyJWT": "2.13.0",  # allauth verifies Google's id_token with it
    "cryptography": "48.0.1",
    "urllib3": "2.7.0",
    "requests": "2.33.1",
    "idna": "3.15",
    "pyasn1": "0.6.4",
    "anyio": "4.14.2",
}


def _parts(v):
    return tuple(int(n) for n in re.findall(r"\d+", v)[:3])


class DependenciesAreAboveTheirAdvisories(TestCase):
    def test_installed_versions(self):
        stale = []
        for name, floor in SECURITY_FLOORS.items():
            try:
                have = version(name)
            except PackageNotFoundError:
                continue  # a transitive that this venv does not pull in
            if _parts(have) < _parts(floor):
                stale.append(f"{name} {have} < {floor}")
        self.assertEqual(stale, [])
