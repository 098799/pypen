"""Keep a Python server's heap small on glibc (kit README §7, "cap glibc's malloc arenas").

KIT-MALLOC: v2 2026-09-29

The canonical copy is ~/apps/kit/py/malloc.py. Apps carry a byte-identical copy
(museum and sudoku deploy by `git archive` to bae, so nothing may import
across repos); `fleet-check` (check `kit`) warns when a copy differs. Change
the canonical file, bump the stamp, copy it out — never edit a copy.

Why: glibc gives each new thread its own malloc arena (up to 8 per core, 64 MB
of address space each), and memory freed inside an arena mostly stays there.
A server that starts a thread per request (`ThreadingHTTPServer`), or does
image or model work in a thread pool, grows arena by arena and never shrinks.
In four days four apps found this and fixed it alone:

  - genesis-backend: 1,944 MB RSS, 1.55 GB of it 16 fragmented arenas;
    `mallopt(M_ARENA_MAX, 2)` in main() → 190-226 MB for the same session.
  - imagine: `malloc_trim(0)` after each image decode, 171 → 51 MB.
  - pod and twitter: `malloc_trim(0)` after dropping the TTS model,
    1,330 → 91 MB and 534 → 84 MB.

The cap alone is NOT enough, and can be worse: with two arenas the request
threads share the main heap, and a hole in its middle never goes back to the
kernel. On a copy of fidelive (288 page views from 48 threads, then 3 s idle):

    default glibc          peak 358 MB, idle 198 MB
    cap only (v1)          peak 344 MB, idle 315 MB   <- worse
    trim every 1 s         peak 330 MB, idle 157 MB
    cap + trim every 1 s   peak 333 MB, idle 151 MB   (one trim: < 10 ms)

So an app calls `start()`, which does both. Stdlib only; every call is a no-op
(False) where glibc is absent:

  - `start(every=15)` — once, at import of the app module or in main(),
    before the first thread starts: `cap_arenas()`, then a daemon thread that
    calls `trim()` every `every` seconds. Calling it again does nothing.

  - `trim()` — also right after a big piece of work is freed (an image
    decoded, a model dropped), so the pages go back at once. Hands free heap
    pages back to the kernel; costs a few ms. True when glibc released any.

  - `cap_arenas()` — the cap on its own; skipped when the unit already sets
    `MALLOC_ARENA_MAX` (glibc read that at start). Use `start()` instead.
"""

import ctypes
import os
import threading
import time

M_ARENA_MAX = -8  # from glibc's <malloc.h>


def _glibc():
    try:
        libc = ctypes.CDLL(None)  # the C library this process already runs on
        libc.mallopt, libc.malloc_trim
    except (OSError, AttributeError):  # not glibc (musl, macOS): nothing to tune
        return None
    return libc


_libc = _glibc()


def cap_arenas(n: int = 2) -> bool:
    """Let at most `n` malloc arenas exist. Call before the first thread."""
    if _libc is None or os.environ.get("MALLOC_ARENA_MAX"):
        return False
    return _libc.mallopt(M_ARENA_MAX, n) == 1


def trim() -> bool:
    """Give freed heap pages back to the kernel (glibc's malloc_trim(0))."""
    if _libc is None:
        return False
    return _libc.malloc_trim(0) == 1


_started = False


def start(every: float = 15.0) -> bool:
    """Cap the arenas and trim every `every` seconds. Call before the first thread."""
    global _started
    if _libc is None or _started:
        return False
    _started = True
    cap_arenas()

    def loop():
        while True:
            time.sleep(every)
            trim()

    threading.Thread(target=loop, name="kit-malloc-trim", daemon=True).start()
    return True
