import hashlib
import json
from pathlib import Path

from django.http import HttpResponse, JsonResponse


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


KITSW = {
    "app": "pypen",
    "build": _build(),
    "name": "Pens",
    "where": "internet",
    "colors": {
        "light": {"bg": "#f4ecd8", "fg": "#1b2a4a", "dim": "#5a4b2e", "accent": "#7a1f2b", "line": "#d6c9a5"},
        "dark": {"bg": "#13161c", "fg": "#ece2c8", "dim": "#b9ad92", "accent": "#e08a94", "line": "#2b303b"},
    },
    "files": ["/static/"],
    "skip": ["/accounts/", "/admin/", "/api/", "/media/", "/i/", "/undo/"],
    "takeover": True,
}
_SW_JS = "self.KITSW = " + json.dumps(KITSW) + ";\n" + (_HERE / "_sw.js").read_text()


_ICON_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#f4ecd8"/>
      <stop offset="100%" stop-color="#e9dfc5"/>
    </linearGradient>
    <linearGradient id="nib" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#2a3b5b"/>
      <stop offset="100%" stop-color="#0e1628"/>
    </linearGradient>
    <linearGradient id="nibDark" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#394b6a"/>
      <stop offset="100%" stop-color="#1b2a4a"/>
    </linearGradient>
  </defs>
  <rect width="512" height="512" fill="url(#bg)" rx="72"/>
  <g transform="translate(256 256)">
    <path d="M 0 -140
             C 55 -140, 95 -100, 95 -50
             L 70 140
             L 0 190
             L -70 140
             L -95 -50
             C -95 -100, -55 -140, 0 -140 Z"
          fill="url(#nib)" stroke="#7a1f2b" stroke-width="3"/>
    <circle cx="0" cy="-10" r="16" fill="url(#bg)"/>
    <line x1="0" y1="6" x2="0" y2="170" stroke="#f4ecd8" stroke-width="5" stroke-linecap="round"/>
  </g>
</svg>
"""


_ICON_MASKABLE = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="nib" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#2a3b5b"/>
      <stop offset="100%" stop-color="#0e1628"/>
    </linearGradient>
  </defs>
  <rect width="512" height="512" fill="#f4ecd8"/>
  <g transform="translate(256 256) scale(0.72)">
    <path d="M 0 -140
             C 55 -140, 95 -100, 95 -50
             L 70 140
             L 0 190
             L -70 140
             L -95 -50
             C -95 -100, -55 -140, 0 -140 Z"
          fill="url(#nib)" stroke="#7a1f2b" stroke-width="3"/>
    <circle cx="0" cy="-10" r="16" fill="#f4ecd8"/>
    <line x1="0" y1="6" x2="0" y2="170" stroke="#f4ecd8" stroke-width="5" stroke-linecap="round"/>
  </g>
</svg>
"""


def service_worker(request):
    resp = HttpResponse(_SW_JS, content_type="application/javascript")
    resp["Service-Worker-Allowed"] = "/"
    resp["Cache-Control"] = "no-cache"
    return resp


def manifest(request):
    data = {
        "name": "Grining Fountain Pens",
        "short_name": "Pens",
        "description": "Tomek's fountain-pen bureau.",
        "start_url": "/dashboard/",
        "scope": "/",
        "display": "standalone",
        "display_override": ["standalone", "minimal-ui"],
        "orientation": "portrait",
        "background_color": "#f4ecd8",
        "theme_color": "#1b2a4a",
        "icons": [
            {"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml"},
            {"src": "/icon-maskable.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "maskable"},
        ],
        "categories": ["lifestyle", "personalization"],
    }
    return JsonResponse(data)


def icon(request):
    return HttpResponse(_ICON_SVG, content_type="image/svg+xml")


def icon_maskable(request):
    return HttpResponse(_ICON_MASKABLE, content_type="image/svg+xml")
