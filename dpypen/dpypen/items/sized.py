"""Pictures at the size the page draws them (kit README §5.6, PYPEN-3).

The stored photos are 1800-2400 px JPEGs (~250-300 KB). A pen page drew the
first one into a frame 390 px wide on a phone; a writing sample or a swatch
went whole into its tile. Here a page draws a WebP copy instead, made by the
kit's `webp.py` (a byte copy, KIT-WEBP) the first time and kept on disk:

    MEDIA_ROOT/sized/<edge>/<stored name without .jpg>.webp

The stored name is a random 128-bit token (models._random_media_path), so the
copy's name is as unguessable as the photo's. nginx serves it with the rest of
/media/. A stored file is never written again under its name (an edit or a
turn saves a new one), so the copy never goes stale under nginx's `immutable`.

The photo viewer still opens the stored file: the page passes it as the
viewer's url, and only draws the copy.

    sized.url(field) -> url    the copy's, or the stored file's when no copy
                               is smaller (webp.best) or the file is not on disk
    sized.prune() -> n         remove copies whose photo is gone
                               (manage.py sized_copies, run by the deploy)
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings

from dpypen.items import webp

# The kit's rule is CSS px x 3 (§5.6). The pen page's photo frame is ~360 CSS
# px wide on a phone (x3 = 1080) and up to ~560 on a desk (x2 = 1120); a
# writing sample or a swatch is one tile to a row on a phone, ~360 px too. On
# the live photos 1200 px is 16-29 KB against the stored 254-299 KB JPEG
# (900 px, which the ticket guessed, would save another 5-10 KB and be soft on
# a 3x phone).
EDGE = 1200
EDGES = (EDGE,)


def _root() -> Path:
    return Path(settings.MEDIA_ROOT)


def _dest(name: str, edge: int) -> Path:
    stem = name.rsplit(".", 1)[0]
    return _root() / "sized" / str(edge) / f"{stem}.webp"


def url(field, edge: int = EDGE) -> str | None:
    """The url a page should draw `field` (an ImageField's file) with, `edge`
    px on its long side at most."""
    if not field:
        return None
    try:
        src = Path(field.path)
        out = webp.best(src, _dest(field.name, edge), edge)
    except (OSError, ValueError, NotImplementedError):
        return field.url
    if out == src:
        return field.url
    return settings.MEDIA_URL + out.relative_to(_root()).as_posix()


def prune() -> int:
    """Remove every copy whose stored photo is gone; returns how many."""
    root = _root()
    gone = 0
    for edge in EDGES:
        base = root / "sized" / str(edge)
        if not base.is_dir():
            continue
        for copy in base.rglob("*.webp"):
            stem = root / copy.relative_to(base).with_suffix("")
            if not any(stem.with_name(stem.name + ext).exists() for ext in (".jpg", ".jpeg", ".png")):
                copy.unlink(missing_ok=True)
                gone += 1
    return gone
