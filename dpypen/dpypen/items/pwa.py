import hashlib
import json
from pathlib import Path

from django.http import HttpResponse, JsonResponse
from django.templatetags.static import static

from dpypen.items import whatsnew as kit_whatsnew
from dpypen.items.auth import login_or_guest_required


# The kit's service worker (KIT-SW): _sw.js is ~/apps/kit/snippets/sw.js byte for byte
# (never edit it; copy a new one from the kit). /sw.js = these settings + that text.
# Navigations are network first and kept for offline; the Google OAuth hand-off is
# under /accounts/, which the worker never touches (`skip`), nor the admin, the
# JSON, the media (Range) or the GETs that act (an invite, an undo). Writes are
# never touched. `build` is a hash of the app's code, templates and static files,
# so the worker's bytes change on a deploy that changes them, and only then.
_HERE = Path(__file__).resolve().parent
_PKG = _HERE.parent


def _build() -> str:
    h = hashlib.sha256()
    for f in sorted(_PKG.rglob("*")):
        if f.suffix in {".py", ".html", ".css", ".js", ".svg", ".json"} and f.is_file() \
                and "__pycache__" not in f.parts and "migrations" not in f.parts:
            h.update(str(f.relative_to(_PKG)).encode() + b"\0" + f.read_bytes())
    return h.hexdigest()[:12]


# The app's one name (kit §4 Fleet UX "Names", PYPEN-9): the home-screen tile,
# short_name, the apple title, every tab title `‹page› · Grining Pens`, the
# offline page, the keyboard layer and the Install row. Short enough for a tile,
# full enough for a public browser tab.
APP_NAME = "Grining Pens"

KITSW = {
    "app": "pypen",
    "build": _build(),
    "name": APP_NAME,
    "where": "internet",
    "colors": {
        "light": {"bg": "#f4ecd8", "fg": "#1b2a4a", "dim": "#5a4b2e", "accent": "#7a1f2b", "line": "#d6c9a5"},
        "dark": {"bg": "#13161c", "fg": "#ece2c8", "dim": "#b9ad92", "accent": "#e08a94", "line": "#2b303b"},
    },
    "files": ["/static/", "/kit/"],
    "skip": ["/accounts/", "/admin/", "/api/", "/media/", "/i/", "/undo/"],
    "takeover": True,
}
# The app's part of the worker, after the kit's (its kitSW.route hook).
# whitenoise names a changed /static/ file anew (name.<12 hex>.ext), so such a
# file is content-addressed like a ?v= URL: the kept copy first, the network
# only for a name never seen. The kit's file() went to the network first for
# them and wrote each one into Cache Storage again on every page (~20 writes a
# load), and once the HTTP cache's day ran out every asset was asked again
# (speed pass, AUDIT.md P10). Kept in the kit's files cache, at most MAX_FILES.
_SW_APP = """
(function () {
  var HASHED = /^\\/static\\/.+\\.[0-9a-f]{12}\\.[a-z0-9]+$/, MAX_FILES = 400;
  kitSW.route(function (event, url) {
    var req = event.request;
    if (req.method !== "GET" || req.headers.has("Range") || !HASHED.test(url.pathname)) return;
    return caches.open(kitSW.caches.files).then(function (cache) {
      return cache.match(req).then(function (hit) {
        if (hit) return hit;
        return fetch(req).then(function (resp) {
          if (resp.status === 200 && resp.type === "basic") {
            event.waitUntil(cache.put(req, resp.clone()).then(function () { return cache.keys(); }).then(function (keys) {
              return Promise.all(keys.slice(0, Math.max(0, keys.length - MAX_FILES)).map(function (k) { return cache.delete(k); }));
            }));
          }
          return resp;
        });
      });
    });
  });
})();
"""
_SW_JS = "self.KITSW = " + json.dumps(KITSW) + ";\n" + (_HERE / "_sw.js").read_text() + _SW_APP


# The icon (the tower standard, kit §4 "Icons"): one navy nib, its breather
# hole and slit in the paper colour, inside a dashed ring, the rotation, with
# one oxblood dot on it, the next pen due; a quiet outer ring round all of it.
# pens (the catalogue) draws the same nib three times. Flat on the paper
# (#f4ecd8, the manifest's background_color, the colour of the phone's splash)
# edge to edge, so the splash shows no tile. _NIB is drawn in a 64 box round
# (32, 32); its outer edge is the ring, 26.5 from the centre.
# tools/make_icons.py reads these three strings and draws the PNGs in
# static/items/icons/.
_NIB = (
    '<circle cx="32" cy="32" r="25.5" fill="none" stroke="#b9ad92" stroke-width="2"/>'
    '<circle cx="32" cy="32" r="18.5" fill="none" stroke="#1b2a4a" stroke-width="2"'
    ' stroke-dasharray="3.63 2.18" transform="rotate(-90 32 32)"/>'
    '<path d="M32 45 L24 31 V20 H40 V31 Z" fill="#1b2a4a"/>'
    '<circle cx="32" cy="30" r="2.4" fill="#f4ecd8"/>'
    '<path d="M32 32 V45" stroke="#f4ecd8" stroke-width="2"/>'
    '<circle cx="45" cy="19" r="3.2" fill="#7a1f2b"/>'
)


def _icon_svg(scale: float) -> str:
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            '<rect width="64" height="64" fill="#f4ecd8"/>'
            f'<g transform="translate(32 32) scale({scale}) translate(-32 -32)">' + _NIB + '</g></svg>\n')


# "any": the sign at full size (0.41 of the width). maskable: 26.5 x 0.75 / 64
# = 0.31 of the width, inside the circle of 1/3 the width that Android 12+
# keeps on the splash.
_ICON_SVG = _icon_svg(1.0)
_ICON_MASKABLE = _icon_svg(0.75)


def service_worker(request):
    resp = HttpResponse(_SW_JS, content_type="application/javascript")
    resp["Service-Worker-Allowed"] = "/"
    resp["Cache-Control"] = "no-cache"
    return resp


def manifest(request):
    data = {
        "id": "/",
        "name": APP_NAME,
        "short_name": APP_NAME,
        "description": "Tomek Grining's fountain pen collection.",
        "start_url": "/dashboard/",
        "scope": "/",
        "display": "standalone",
        "display_override": ["standalone", "minimal-ui"],
        "orientation": "portrait",
        "background_color": "#f4ecd8",
        "theme_color": "#1b2a4a",
        # The kit's set (README §4 "Icons"): committed PNGs 192 + 512 + 512
        # maskable, drawn from the SVGs above by tools/make_icons.py, and the SVGs for
        # whoever takes them. iOS takes neither from here: its home-screen
        # icon is the apple-touch-icon link, which must be a PNG (an SVG there
        # gave a screenshot of the page).
        "icons": [
            {"src": static("items/icons/icon-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": static("items/icons/icon-512.png"), "sizes": "512x512", "type": "image/png"},
            {"src": static("items/icons/icon-maskable-512.png"), "sizes": "512x512", "type": "image/png",
             "purpose": "maskable"},
            {"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml"},
            {"src": "/icon-maskable.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "maskable"},
        ],
        "categories": ["lifestyle", "personalization"],
    }
    return JsonResponse(data)


def _icon(request, svg: str):
    """The icon is in every page's header: with no cache header at all, each
    page load waited a round trip for it before its load event (speed pass,
    AUDIT.md P21). A day, then a 304 on its ETag."""
    from django.utils.http import quote_etag

    tag = quote_etag(hashlib.sha256(svg.encode()).hexdigest()[:16])
    if tag in request.headers.get("If-None-Match", ""):
        resp = HttpResponse(status=304)
    else:
        resp = HttpResponse(svg, content_type="image/svg+xml")
    resp["ETag"] = tag
    resp["Cache-Control"] = "public, max-age=86400"
    return resp


def icon(request):
    return _icon(request, _ICON_SVG)


def icon_maskable(request):
    return _icon(request, _ICON_MASKABLE)


def build_context(request):
    """Template context processor: the build the page was made by.

    The kit's update toast (_update.html) compares it with /api/version: the
    worker takes over at install (`takeover`), so no waiting worker would ever
    tell an open page about a deploy."""
    return {"kit_build": KITSW["build"], "app_name": APP_NAME}


def version(request):
    """The build now served, for the update toast. No data: open to anyone."""
    resp = JsonResponse({"build": KITSW["build"]})
    resp["Cache-Control"] = "no-store"
    return resp


# What's new (kit README §4): the log is a file in the repo, newest entry on
# top; kit_whatsnew (whatsnew.py, a byte copy of the kit's) answers it as a list.
_WHATSNEW = _HERE / "whatsnew.json"


@login_or_guest_required
def whatsnew(request):
    doc = json.loads(_WHATSNEW.read_text(encoding="utf-8"))
    status, body = kit_whatsnew.answer(doc, request.META.get("QUERY_STRING", ""))
    resp = JsonResponse(body, status=status)
    resp["Cache-Control"] = "no-cache"
    return resp
