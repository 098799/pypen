"""Where a form goes when it is done: back to the page it was opened from.

A fill finished on the desk stays on the desk, an inking edited from a pen's
page goes back to that pen (UX pass, 10 Nov 2026: every one of them went to the
inkings list, a page behind More, so "finish and ink it again" was seven taps).

The page before is `next` (a form's hidden field or the address), else the
Referer, which the browser sends same-origin only (Referrer-Policy
same-origin). Only an address on this host counts (Django's own check, which
also refuses `/\\evil.example`), and never the form's own address.
"""

from urllib.parse import urlsplit

from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme


def _local(request, url):
    if not url or not url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return None
    parts = urlsplit(url)
    path = parts.path or "/"
    return path + (f"?{parts.query}" if parts.query else "")


def came_from(request, default, *, avoid=()):
    """The page before this one, as a local path, or `default`.

    `avoid`: path prefixes that must not be the answer (a deleted record's
    own pages)."""
    own = request.path
    for url in (request.POST.get("next"), request.GET.get("next"), request.META.get("HTTP_REFERER")):
        path = _local(request, url)
        if not path:
            continue
        bare = path.split("?", 1)[0]
        if bare == own or any(bare.startswith(a) for a in avoid):
            continue
        return path
    return default


def back(request, default, *, avoid=()):
    return redirect(came_from(request, default, avoid=avoid))
