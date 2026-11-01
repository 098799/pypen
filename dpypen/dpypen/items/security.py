"""Headers every answer carries, and what Sign out and Leave wipe (PYPEN-4).

Django's SecurityMiddleware already sends nosniff, Referrer-Policy same-origin
and Cross-Origin-Opener-Policy; nginx adds HSTS; XFrameOptionsMiddleware sends
DENY. This adds the rest.

Content-Security-Policy, with inline script allowed. A strict policy (a nonce
on every script) was weighed and turned down, for now: the pages carry ~35
inline <script> blocks and ~20 on*= handlers, several of them inside the kit's
byte-for-byte snippets (_settings.html, _keys.html, _toast.html) that this app
may not edit; hx-boost swaps in each new page's scripts, which would need
htmx's inlineScriptNonce kept in step; and a missed one is a dead button on the
live site. What an injected script could do is small here — one collection,
Django autoescapes every template, no |safe on stored text — and the policy
still shuts what matters most: no script, style, font, image or fetch from
another origin (so nothing can be sent away with an <img> or a fetch), no
<object>, no <base> rewrite, no framing, no form posted off the site except to
Google's sign-in.

Clear-Site-Data on Sign out and Leave: on a shared phone or desktop, the
service worker's kept pages, the recent searches of the palette (localStorage)
and the HTTP cache all held the collection after the person had gone. The page
also tells the worker KIT_FORGET, but that is a message raced against a
navigation; this header is the browser's own promise. It also forgets the
theme choice — the price of forgetting everything.
"""

from django.utils.cache import patch_cache_control

CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self'",
        "connect-src 'self'",
        "media-src 'self'",
        "worker-src 'self'",
        "manifest-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self' https://accounts.google.com",
        "frame-ancestors 'none'",
    ]
)

PERMISSIONS = "camera=(), microphone=(), geolocation=(), payment=(), usb=(), serial=(), bluetooth=()"

# Paths whose successful POST ends a visit: allauth's sign-out, the guest's Leave.
FORGET_ON = ("/accounts/logout/", "/i/leave/")
CLEAR_SITE_DATA = '"cache", "storage"'


class SecurityHeaders:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.headers.setdefault("Content-Security-Policy", CSP)
        response.headers.setdefault("Permissions-Policy", PERMISSIONS)

        if request.method == "POST" and request.path in FORGET_ON and response.status_code in (301, 302, 303):
            response["Clear-Site-Data"] = CLEAR_SITE_DATA

        # A page drawn for a signed-in owner or a guest is theirs alone: no
        # shared cache may keep it. (The service worker still keeps it for
        # offline — `private` is not `no-store` — and forgets it on sign-out.)
        if "Cache-Control" not in response.headers and _is_page(response) and _is_visitor(request):
            patch_cache_control(response, private=True)
        return response


def _is_page(response):
    return response.get("Content-Type", "").startswith("text/html")


def _is_visitor(request):
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return True
    session = getattr(request, "session", None)
    from dpypen.items.auth import GUEST_SESSION_KEY

    return bool(session is not None and session.get(GUEST_SESSION_KEY))
