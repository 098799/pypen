"""A picture at the size the page draws it, as WebP (kit README §5, "small WebP copies").

KIT-WEBP: v1 2026-09-30

The canonical copy is ~/apps/kit/py/webp.py. Apps carry a byte-identical copy
(museum and sudoku deploy by `git archive` to bae, so nothing may import
across repos); `fleet-check` (check `kit`) warns when a copy differs. Change
the canonical file, bump the stamp, copy it out — never edit a copy.

Why: in six days burn's agents wrote this same routine seven times, app by
app — imagine's list thumbs and full-size view copy, twitter's 96 px faces and
1080 px card photos, museum's grid thumbs and player faces, pod's slimmed
article pictures — each one cutting a page's picture bytes by 50-95 %
(twitter faces 31 MB -> 1.8 MB, imagine viewer 15.7 -> 3.05 MB). The copies
had drifted: three wrote the file in place, so a request that raced the first
one could serve half a WebP; two ignored the EXIF turn, so a phone photo came
out on its side; two never made a stale copy again; and each chose its own
exception list, so a broken file was a 500 in one app and the original in the
next. This module does each of those once.

Pillow is imported inside the calls, never at module scope: museum's public
mirror ran a venv without Pillow once, and a top-level import took the whole
site down for a thumbnail.

  - `encode(data, edge, fit=, quality=)` -> WebP bytes, or None when the
    input is not a still Pillow can read (animated GIF/WebP, SVG, garbage).
    `data` is bytes or a path. `edge` bounds the picture, never enlarges it:
      fit="long"   the long edge is at most `edge` (the default)
      fit="width"  the width is at most `edge` (a column of cards)
      fit="square" a centre crop, `edge` square at most (faces, avatars)
    `edge=None` keeps the size and only re-encodes. EXIF turn applied (WebP
    keeps none), alpha kept when there is any, a JPEG decoded at reduced
    size when it can (`draft`, 3-10x faster on 12 MP phone photos).
  - `save(data, dest)` — write bytes so no reader ever sees half a file:
    a per-thread temp name, then an atomic rename. Makes the directory.
  - `copy(src, dest, edge, ...)` -> dest, made once and made again when the
    source is newer; None when `encode` gives None. Two threads racing on one
    new picture both get a whole file.
  - `best(src, dest, edge, ..., keep=0.9)` -> the path a page should get:
    the copy, or `src` when no copy could be made or it did not come in under
    `keep` x the source's size (a small flat PNG often does not).
  - `shrink(data, edge, ..., keep=0.9)` -> the bytes form of `best`: WebP
    bytes, or None to keep `data` as it is.

Call `malloc.trim()` after a batch of these in a long-lived server: a decode
is tens of MB and glibc keeps the pages otherwise (kit README §7).
"""

from __future__ import annotations

import io
import os
import threading
from pathlib import Path

__all__ = ["encode", "save", "copy", "best", "shrink"]

FITS = ("long", "width", "square")


def encode(data, edge: int | None, *, fit: str = "long", quality: int = 80,
           method: int = 4) -> bytes | None:
    """`data` (bytes or a path) as WebP no bigger than `edge`; None if it is
    not a still picture Pillow can read."""
    if fit not in FITS:
        raise ValueError(f"fit must be one of {FITS}, not {fit!r}")
    from PIL import Image, ImageOps

    src = io.BytesIO(data) if isinstance(data, (bytes, bytearray, memoryview)) else data
    try:
        with Image.open(src) as im:
            if getattr(im, "is_animated", False):
                return None
            if edge and im.format == "JPEG":
                im.draft("RGB", (edge, edge))
            im = ImageOps.exif_transpose(im)
            alpha = im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info
            im = im.convert("RGBA" if alpha else "RGB")
            if edge:
                im = _fit(im, edge, fit, Image.Resampling.LANCZOS)
            out = io.BytesIO()
            im.save(out, "WEBP", quality=quality, method=method)
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        # OSError covers UnidentifiedImageError and truncated files; Pillow
        # raises SyntaxError for some broken PNG/GIF headers.
        return None
    return out.getvalue()


def _fit(im, edge: int, fit: str, resample):
    w, h = im.size
    if fit == "square":
        side = min(w, h)
        if (w, h) != (side, side):
            left, top = (w - side) // 2, (h - side) // 2
            im = im.crop((left, top, left + side, top + side))
        return im.resize((edge, edge), resample) if side > edge else im
    if fit == "width":
        if w <= edge:
            return im
        return im.resize((edge, max(1, round(h * edge / w))), resample)
    if max(w, h) <= edge:
        return im
    scale = edge / max(w, h)
    return im.resize((max(1, round(w * scale)), max(1, round(h * scale))), resample)


def save(data: bytes, dest) -> Path:
    """Write `data` to `dest` atomically; returns `dest` as a Path."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f"{dest.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)
    return dest


def _fresh(src: Path, dest: Path) -> bool:
    try:
        return dest.stat().st_mtime >= src.stat().st_mtime
    except FileNotFoundError:
        return False


def copy(src, dest, edge: int | None, *, fit: str = "long", quality: int = 80,
         method: int = 4) -> Path | None:
    """The WebP copy of file `src` at `dest`, made if missing or older than
    `src`. None if `src` is not a still picture (or is gone)."""
    src, dest = Path(src), Path(dest)
    if _fresh(src, dest):
        return dest
    try:
        data = encode(src, edge, fit=fit, quality=quality, method=method)
    except FileNotFoundError:
        return None
    if data is None:
        return None
    return save(data, dest)


def best(src, dest, edge: int | None, *, fit: str = "long", quality: int = 80,
         method: int = 4, keep: float = 0.9) -> Path:
    """The file a page should get: the copy at `dest`, or `src` itself when no
    copy could be made or the copy is not under `keep` x the size of `src`."""
    src = Path(src)
    out = copy(src, dest, edge, fit=fit, quality=quality, method=method)
    if out is not None and out.stat().st_size < keep * src.stat().st_size:
        return out
    return src


def shrink(data: bytes, edge: int | None, *, fit: str = "long", quality: int = 80,
           method: int = 4, keep: float = 0.9) -> bytes | None:
    """WebP bytes of `data` when they come in under `keep` x its size, else
    None (keep the original: it is animated, unreadable, or already small)."""
    out = encode(data, edge, fit=fit, quality=quality, method=method)
    if out is None or len(out) >= keep * len(data):
        return None
    return out
