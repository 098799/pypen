"""The kit's snippets as cached files, not inline in every page (kit README §5.9).

KIT-SHELL: v1.1 2026-11-07

The canonical copy is ~/apps/kit/py/shell.py. Apps carry a byte-identical
copy (nothing may import across repos); `fleet-check` (check `kit`) warns when
a copy differs. Change the canonical file, bump the stamp, copy it out — never
edit a copy.

Why: an app that `{% include %}`s the kit's snippets sends 60-180 KB of their
style, script and header comments again with every page, and no cache can keep
it (a page is `no-cache`). By 2026-11-07 eight apps had cut the snippets out by
hand (atlas, lemma, burnlog, twitter, tv, pokedex, vac, museum), each with its
own regex: one kept the header comment's example `<script>` as code, one took
`<script>(.*)</script>` greedy, one dropped a second `<style>`, one lost the
stamp `curl | grep KIT-` looks for. The others still sent everything inline.

What it does, stdlib only, no framework import:

    shell = Shell(TEMPLATES, assets)                    # assets: caching.Assets
    shell.css("shell.css", STATIC / "app.css", "_header.html", "_tabs.html")
    shell.js("shell.js", "_layer.js", "_header.html", "_tabs.html",
             raw('window.KITINSTALL = {app: "x"};'), "_install.html")
    app.add_middleware(ShellFiles, shell=shell)        # serves /static/shell.css …
    # in a template: <link rel=stylesheet href="{{ asset('shell.css') }}">
    #                <script defer src="{{ asset('shell.js') }}"></script>

  - A source is a path (relative to the root given to Shell, or absolute) or a
    `raw()` string. A kit `.html` copy gives its one `<style>` to `css()` and
    its `<script>`s to `js()`; its header comment never goes out. A `.js` or
    `.css` file goes whole, its header comment cut to the stamp line. Each
    part is preceded by `/*! KIT-NAME: v… */` (a `/*!` comment: rjsmin and
    rcssmin keep it with `keep_bang_comments=True`), so `curl | grep KIT-`
    still finds what a page runs. A copy with Jinja in it (`{{`, `{%`) or markup
    besides its style and script raises at start: it cannot be cut. A
    `{# … #}` header is read like `<!-- … -->`; `cut(path, markup=True)`
    keeps the rest in `.markup` for the page (`_keys.html`: vac, museum).
  - Scripts are joined with `;` between them, in the order given. One that
    throws at load stops the ones after it in the same file (inline, each
    `<script>` stopped only itself): order the kit's first (`_layer.js` must
    be first: its popstate listener comes before every other).
  - `Shell(..., minify=f)`: `f(name, text) -> text` runs on every file that
    `css()` and `js()` build (burnlog, vac: rjsmin/rcssmin), before its hash.
  - `shell.files` is `{name: (bytes, content type)}`; each file is also
    registered with `assets.add()`, so `asset(name)` gives `?v=<hash>`.
  - `ShellFiles` (ASGI) answers GET and HEAD for `<prefix>/<name>`: a weak
    ETag and 304, gzip made once at level 9 (`Vary: Accept-Encoding`; nginx
    does not gzip it again), `immutable` for the current `?v=`, `no-cache`
    for any other (a page from before a deploy must not pin the new bytes
    under an old name). Other paths go to the app.
  - `shell.answer(path, query, headers)` is the same for any other server
    (http.server, Django): `(status, [(header, value)], body)` or None.
"""

from __future__ import annotations

import gzip
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs

CSS = "text/css; charset=utf-8"
JS = "text/javascript; charset=utf-8"
IMMUTABLE = "public, max-age=31536000, immutable"
NO_CACHE = "no-cache"

_STAMP = re.compile(r"(?:KIT|KEYS)-[A-Z]+: v[^\s*]+(?: \d{4}-\d{2}-\d{2})?")
_HEAD_HTML = re.compile(r"\A\s*(?:<!--(.*?)-->|\{#(.*?)#\})", re.S)
_HEAD_CODE = re.compile(r"\A\s*/\*(.*?)\*/\n?", re.S)
_STYLE = re.compile(r"<style>(.*?)</style>", re.S)
_SCRIPT = re.compile(r"<script>(.*?)</script>", re.S)
_JINJA = re.compile(r"\{\{|\{%|\{#")


@dataclass(frozen=True)
class Part:
    """One source cut into what it gives a style sheet and a script."""
    name: str
    stamp: str | None
    css: str
    js: str
    markup: str = ""

    def label(self) -> str:
        return f"/*! {self.stamp} */\n" if self.stamp else ""


def stamp_of(text: str) -> str | None:
    """`KIT-TOAST: v1.2 2026-10-28`, the stamp line of a kit copy's header."""
    m = _STAMP.search(text)
    return m[0] if m else None


def raw(js: str = "", css: str = "", name: str = "raw") -> Part:
    """The app's own line between parts: a config object a snippet reads."""
    return Part(name, None, css, js)


def cut(path: str | Path, markup: bool = False) -> Part:
    """A source file as a Part. Raises ValueError when it cannot be cut.
    `markup=True` keeps the markup besides the style and script in `.markup`
    (`_keys.html`: its palette and help sheet stay in the page) instead of raising."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".js", ".css"):
        head = _HEAD_CODE.match(text)
        stamp = stamp_of(head[1]) if head else None
        body = text[head.end():] if head and stamp else text
        return Part(path.name, stamp, body if path.suffix == ".css" else "",
                    body if path.suffix == ".js" else "")
    head = _HEAD_HTML.match(text)
    stamp = stamp_of(head[1] or head[2]) if head else None
    body = text[head.end():] if head else text
    styles, scripts = _STYLE.findall(body), _SCRIPT.findall(body)
    rest = re.sub(r"<!--.*?-->", "", _SCRIPT.sub("", _STYLE.sub("", body)), flags=re.S)
    if rest.strip() and not markup:
        raise ValueError(f"{path.name}: markup besides its <style> and <script>: {rest.strip()[:60]!r}")
    if not styles and not scripts:
        raise ValueError(f"{path.name}: no <style> and no <script> to serve")
    if len(styles) > 1:
        raise ValueError(f"{path.name}: more than one <style>")
    if any(_JINJA.search(s) for s in styles + scripts):
        raise ValueError(f"{path.name}: template tags in its code; it cannot be served as a file")
    js = "\n;\n".join(s.strip("\n") + "\n" for s in scripts)
    return Part(path.name, stamp, styles[0].strip("\n") + "\n" if styles else "", js, rest.strip())


def _weak(data: bytes) -> str:
    return 'W/"' + hashlib.blake2b(data, digest_size=10).hexdigest() + '"'


def _matches(header: str | None, tag: str) -> bool:
    if not header:
        return False
    want = tag[2:].strip('"')
    for item in header.split(","):
        item = item.strip()
        if item == "*":
            return True
        item = item.removeprefix("W/").strip('"').removesuffix("-gzip")
        if item == want:
            return True
    return False


class _File:
    __slots__ = ("body", "ctype", "zipped", "tag", "version")

    def __init__(self, body: bytes, ctype: str):
        self.body = body
        self.ctype = ctype
        self.zipped = gzip.compress(body, compresslevel=9, mtime=0)
        self.tag = _weak(body)
        self.version = hashlib.sha256(body).hexdigest()[:10]   # caching.Assets' ?v=


class Shell:
    """Named CSS and JS files built from kit copies and the app's own files."""

    def __init__(self, root: str | Path, assets=None, prefix: str = "/static", minify=None):
        self.root = Path(root)
        self.minify = minify
        self.assets = assets
        self.prefix = prefix.rstrip("/")
        self._files: dict[str, _File] = {}

    def _parts(self, sources) -> list[Part]:
        out = []
        for s in sources:
            if isinstance(s, Part):
                out.append(s)
            else:
                p = Path(s)
                out.append(cut(p if p.is_absolute() else self.root / p))
        return out

    def add(self, name: str, body: bytes | str, ctype: str | None = None) -> bytes:
        """Serve bytes as `<prefix>/<name>` (the content type from the name's ending)."""
        if isinstance(body, str):
            body = body.encode()
        if ctype is None:
            ctype = CSS if name.endswith(".css") else JS if name.endswith(".js") else "application/octet-stream"
        self._files[name] = _File(body, ctype)
        if self.assets is not None:
            self.assets.add(name, body)
        return body

    def css(self, name: str, *sources) -> bytes:
        """One style sheet of the sources' styles, in order."""
        parts = [p for p in self._parts(sources) if p.css]
        return self.add(name, self._small(name, "\n".join(p.label() + p.css for p in parts)), CSS)

    def js(self, name: str, *sources) -> bytes:
        """One script of the sources' scripts, in order, `;` between them."""
        parts = [p for p in self._parts(sources) if p.js]
        return self.add(name, self._small(name, "\n;\n".join(p.label() + p.js.rstrip("\n") + "\n" for p in parts)), JS)

    def _small(self, name: str, text: str) -> str:
        return self.minify(name, text) if self.minify else text

    @property
    def files(self) -> dict[str, tuple[bytes, str]]:
        return {n: (f.body, f.ctype) for n, f in self._files.items()}

    def url(self, name: str) -> str:
        """`<prefix>/<name>?v=<hash>`, as caching.Assets.url gives it."""
        return f"{self.prefix}/{name}?v={self._files[name].version}"

    def answer(self, path: str, query: str = "", headers=None):
        """(status, [(name, value)], body) for `<prefix>/<name>`, or None.
        `headers` is a mapping with lower-case names (or None)."""
        if not path.startswith(self.prefix + "/"):
            return None
        f = self._files.get(path[len(self.prefix) + 1:])
        if f is None:
            return None
        headers = headers or {}
        v = parse_qs(query).get("v", [None])[0]
        out = [("cache-control", IMMUTABLE if v == f.version else NO_CACHE),
               ("etag", f.tag), ("vary", "Accept-Encoding"), ("x-content-type-options", "nosniff")]
        if _matches(headers.get("if-none-match"), f.tag):
            return 304, out, b""
        body = f.body
        if "gzip" in (headers.get("accept-encoding") or "") and len(f.zipped) < len(body):
            body = f.zipped
            out.append(("content-encoding", "gzip"))
        out += [("content-type", f.ctype), ("content-length", str(len(body)))]
        return 200, out, body


class ShellFiles:
    """ASGI middleware: GET and HEAD for the shell's files; the rest to the app."""

    def __init__(self, app, shell: Shell):
        self.app = app
        self.shell = shell

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in ("GET", "HEAD"):
            return await self.app(scope, receive, send)
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers") or []}
        got = self.shell.answer(scope["path"], scope.get("query_string", b"").decode("latin-1"), headers)
        if got is None:
            return await self.app(scope, receive, send)
        status, out, body = got
        await send({"type": "http.response.start", "status": status,
                    "headers": [(k.encode("latin-1"), v.encode("latin-1")) for k, v in out]})
        await send({"type": "http.response.body", "body": b"" if scope["method"] == "HEAD" else body})
