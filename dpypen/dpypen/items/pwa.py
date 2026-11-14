"""The PWA plumbing of a server app: build id, /sw.js, door, manifest (kit README §4 "Offline").

KIT-PWA: v1 2026-11-14

The canonical copy is ~/apps/kit/py/pwa.py. Apps carry a byte-identical copy
(nothing imports across repos); `fleet-check` (check `kit`) warns when a copy
differs. Change the canonical file, bump the stamp, copy it out — never edit a
copy.

Why: by 2026-11-14 every server app with the kit's worker (snippets/sw.js)
wrote the same four things around it by hand, and the copies drifted:

  - The build id (`self.KITSW.build`, `/api/version`) must change on a deploy
    that changes what the browser gets, and only then (update.html offers
    "New version" when it moves). Sixteen copies, eleven rules: imagine and
    tetrafit took `git rev-parse HEAD`, so a commit to the README offered a
    new version, and the mtime fallback did on every checkout; lingo's left
    out the .py files that write its pages (before 2026-10-23 it hashed
    app.js alone); jobs and museum glued each name to its bytes with no
    separator; the file types differed in each copy.
  - `/sw.js` = `self.KITSW = {…};` + the kit's text + the app's hooks: built
    by hand in each app, sent as `text/javascript` or
    `application/javascript`, with or without `no-cache`, read from disk on
    every request in some.
  - The door (`where`): tailnet, internet (bae) or home (a guest door),
    chosen from the Host in five different ways.
  - The manifest: the same ten keys, some with `id`/`scope`, some without.

Four pieces, stdlib only (Starlette only inside `Worker.response()`):

    from . import pwa

    BUILD = pwa.build_id(APP_DIR)                     # 12 hex
    SW = pwa.Worker(TEMPLATES / "_sw.js", {           # the kit's byte copy
        "app": "pod", "build": BUILD, "name": "pod", "where": "tailnet",
        "colors": {...}, "files": ["/static/"], "skip": ["/api/"],
    }, TEMPLATES / "_sw_pod.js")                      # the app's hooks, if any

    @app.get("/sw.js")
    def sw(request: Request):
        return SW.response(where=pwa.door(request.headers.get("host")))

    @app.get("/manifest.json")
    def manifest():
        return JSONResponse(MANIFEST, media_type=pwa.MANIFEST_TYPE)
    MANIFEST = pwa.manifest("pod", bg="#0b0e14", description="…")

  - `build_id(*roots, suffixes=SUFFIXES, skip=())`: the first 12 hex of a
    SHA-256 over every file under the roots (a root may be one file) whose
    suffix is in `suffixes`: its place (root number + relative path), a NUL,
    its bytes, a NUL. Sorted, so the order on disk does not count. Not
    hashed: dot folders (.git, .venv), `__pycache__`, `node_modules`, the
    folder names in `skip`, and pictures (a new picture does not need a new
    worker: the kit's worker asks the network first for files). Pass the
    folders whose files reach the browser or make what does: the package
    (code + templates) and the static folder.
  - `Worker(kit, settings, *hooks)`: `kit` is the path of the app's byte copy
    of snippets/sw.js (checked: its stamp must be in it), `hooks` paths or
    texts of the app's own part, put after it. `settings` needs `app` and
    `build`. `text(**over)` → the worker, with `over` laid over the settings
    (`where=`, `lang=`), built once per distinct `over`. `body()` → bytes,
    `answer()` → `(200, headers, bytes)` for an http.server handler,
    `response()` → a Starlette Response. `TYPE` and `HEADERS` are what it
    goes out with: JavaScript, `no-cache`.
  - `door(host, outside="internet")`: `"tailnet"` for p340.grining.eu and its
    subdomains, else `outside` (`"home"` for an app whose other door is a
    guest door on the home wifi). A port and a final dot are ignored.
  - `manifest(name, *, bg, …)`: the manifest as a dict, `id`, `scope`,
    `start_url` and `display` filled in, and the three icons the kit draws
    (§4 "Icons") under `icons` (a prefix, or a list of your own;
    `icon_list(prefix, maskable)` makes the kit's three).
    `MANIFEST_TYPE` is its media type. Extra keys (`shortcuts`,
    `share_target`, `orientation`) pass through.

`/api/version` stays the app's own three lines: `{"build": BUILD}`, sent
`no-store` (`VERSION_HEADERS`).

Tests: python3 -m pytest ~/apps/kit/py -q
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

# What reaches the browser or makes it. No pictures: see the docstring.
SUFFIXES = (".py", ".html", ".htm", ".jinja", ".j2", ".js", ".mjs", ".css",
            ".json", ".svg", ".webmanifest", ".txt", ".md")
SKIP_DIRS = frozenset({"__pycache__", "node_modules"})

TYPE = "text/javascript; charset=utf-8"
HEADERS = {"Cache-Control": "no-cache"}
VERSION_HEADERS = {"Cache-Control": "no-store"}
MANIFEST_TYPE = "application/manifest+json"
TAILNET = "p340.grining.eu"
STAMP = "KIT-SW:"


def build_id(*roots, suffixes=SUFFIXES, skip=(), length=12) -> str:
    """A content hash of the files under `roots`; see the module docstring."""
    if not roots:
        raise TypeError("build_id() needs at least one folder or file")
    suffixes = tuple(s.lower() for s in suffixes)
    skip = SKIP_DIRS | set(skip)
    h = hashlib.sha256()
    for n, root in enumerate(roots):
        root = Path(root)
        if root.is_file():
            files = [(root.name, root)]
        elif root.is_dir():
            files = []
            for dirpath, dirs, names in os.walk(root):
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in skip]
                for name in names:
                    if name.lower().endswith(suffixes) and not name.startswith("."):
                        p = Path(dirpath) / name
                        files.append((p.relative_to(root).as_posix(), p))
        else:
            raise FileNotFoundError(f"build_id(): {root} is neither a file nor a folder")
        for rel, p in sorted(files):
            h.update(f"{n}:{rel}".encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()[:length]


def door(host, outside="internet") -> str:
    """"tailnet" for p340.grining.eu and below it, else `outside`."""
    h = (host or "").strip().lower()
    if h.startswith("["):                 # [::1]:8000
        h = h.partition("]")[0] + "]"
    else:
        h = h.partition(":")[0]
    h = h.rstrip(".")
    return "tailnet" if h == TAILNET or h.endswith("." + TAILNET) else outside


class Worker:
    """/sw.js: the settings, the kit's worker, the app's hooks."""

    TYPE = TYPE
    HEADERS = HEADERS

    def __init__(self, kit, settings: dict, *hooks):
        kit_text = Path(kit).read_text(encoding="utf-8")
        if STAMP not in kit_text[:400]:
            raise ValueError(f"{kit} is not the kit's worker (no {STAMP} stamp at its top)")
        for key in ("app", "build"):
            if not settings.get(key):
                raise ValueError(f"Worker settings need {key!r}")
        self.settings = dict(settings)
        parts = [kit_text]
        for hook in hooks:
            parts.append(hook.read_text(encoding="utf-8") if isinstance(hook, Path) else str(hook))
        self._code = "\n".join(p.rstrip("\n") for p in parts) + "\n"
        self._texts: dict[str, str] = {}

    @property
    def build(self) -> str:
        return self.settings["build"]

    def text(self, **over) -> str:
        key = json.dumps(over, sort_keys=True)
        t = self._texts.get(key)
        if t is None:
            settings = {**self.settings, **over}
            t = "self.KITSW = %s;\n%s" % (json.dumps(settings, ensure_ascii=False), self._code)
            self._texts[key] = t
        return t

    def body(self, **over) -> bytes:
        return self.text(**over).encode("utf-8")

    def answer(self, **over):
        """(status, headers, body) for an http.server handler."""
        body = self.body(**over)
        return 200, {"Content-Type": TYPE, "Content-Length": str(len(body)), **HEADERS}, body

    def response(self, **over):
        from starlette.responses import Response
        return Response(self.body(**over), media_type=TYPE, headers=dict(HEADERS))


def icon_list(prefix="/", maskable="icon-maskable-512.png") -> list:
    """The kit's three PNG icons under `prefix`."""
    p = prefix if prefix.endswith("/") else prefix + "/"
    return [
        {"src": p + "icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": p + "icon-512.png", "sizes": "512x512", "type": "image/png"},
        {"src": p + maskable, "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ]


def manifest(name, *, bg, theme=None, short_name=None, description=None,
             start_url="/", scope="/", id="/", display="standalone",
             icons="/", maskable="icon-maskable-512.png", **extra) -> dict:
    """The web app manifest; see the module docstring."""
    m = {"id": id, "name": name, "short_name": short_name or name}
    if description:
        m["description"] = description
    m.update({"start_url": start_url, "scope": scope, "display": display,
              "background_color": bg, "theme_color": theme or bg})
    m["icons"] = icon_list(icons, maskable) if isinstance(icons, str) else list(icons)
    m.update(extra)
    return m
