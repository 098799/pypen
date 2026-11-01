"""What an error answers: a page for a person, JSON for a script (kit README §5).

KIT-ERRORS: v3 2026-10-21

The canonical copy is ~/apps/kit/py/errors.py. Apps carry a byte-identical
copy (museum deploys by `git archive` to bae, so nothing may import across
repos); `fleet-check` (check `kit`) warns when a copy differs. Change the
canonical file, bump the stamp, copy it out — never edit a copy.

Why: FastAPI answers every error with JSON (`{"detail":"Not Found"}`) and
Starlette a bare "Internal Server Error". In an app on a phone's home screen
that is a dead end: no header, no nav, no Back button, 980 px wide. Each app
fixed it alone, after its own audit, with its own 20–60 lines: pod, museum,
twitter, igarchive, vac, tv, burnlog, atlas, lemma (2026-10-01 … 10-21), each
with its own idea of "is this a person?" and its own holes: a 404 raised by the
router as Starlette's base class slipped past a handler on FastAPI's subclass
(twitter); a bad `?page=` was a raw 422 list (pod, museum, twitter); an id past
2**63 was a 500 (pod, museum, vac: 16 routes in pod); a 500 left without the
anti-framing headers, because it comes from outside every middleware (twitter).

The rule: a navigation gets a page in the app's chrome with a way on; a fetch,
an `<img>`, a feed reader and anything under `/api/` keeps JSON.

Framework-free core (stdlib; an `http.server` app uses these directly):

  - `wants_page(method, path, headers, api=("/api/",), files=("/static/",),
    soft=("x-soft-nav",))` → True for a person's navigation. `api` prefixes
    are never a page. A fetch that carries a `soft` header is soft navigation
    asking for a page (snippets/softnav.html sends `X-Soft-Nav: 1`; museum
    adds its own): it gets the chrome, not JSON and a second, hard load.
    Else `Sec-Fetch-Mode: navigate` decides when the browser sends it (a form
    POST is a navigation too); without it (curl, an old client) a GET or HEAD
    that accepts `text/html`. `files` prefixes only when the browser says
    "navigate".
    `headers` is any mapping with `.get()`; a plain dict needs lower-case keys.
  - `describe(status, detail=None, method="GET", fields=())` → an `Error`
    with `status`, `title` (a heading a person reads), `text` (one sentence:
    the app's own `detail` when it gave one, else the kit's words), `detail`,
    `fields` (names of the parameters a 422 refused).
  - `plain_page(err, app="")` → a small self-contained HTML page (system
    colours, a link home and to the p340 index). The fallback when the app's
    page cannot be drawn, or for a client that must not see the app's chrome.

Starlette / FastAPI:

        from .errors import install
        install(app, page=error_page)        # after `app = FastAPI(...)`

        def error_page(request, err):        # sync (runs in the pool) or async
            return templates.TemplateResponse(request, "error.html", {"err": err})

  `install` registers handlers for Starlette's `HTTPException` (the base
  class, so the router's own 404 and 405 are caught), FastAPI's
  `RequestValidationError` (only when the process has imported FastAPI
  already: errors.py never imports it — twitter runs on Starlette alone to
  save 21 MB and ~360 ms at start), `OverflowError` (404 for a
  GET, 422 for a write) and `Exception` (500; Starlette still logs the
  traceback). A WebSocket's exceptions pass through untouched.
  `validation=(ExcClass, json_handler)` for an app with its own validation
  error (twitter's `lite.RequestValidationError`): the same 422 page naming
  the fields (`exc.errors()`), and `await json_handler(request, exc)` for a
  fetch. It returns `respond`: `await respond(request, status, detail=None,
  fields=())` is the
  same answer, for an app's own exception handler (museum: a file name past
  255 bytes, `OSError` ENAMETOOLONG, is a 404). No handler for all of
  `OSError`: a client that hangs up mid-stream raises one after the answer
  started, and a handler turns that into a RuntimeError.
  `page` returns a Response (its status is set to the error's), or None for
  `plain_page` — do that for a public path, so a stranger never sees the
  app's counts. `page=None` = `plain_page` always. A page that raises falls
  back to `plain_page` and is logged. `json(request, err)` replaces the JSON
  answer (tv's frontend reads `{"ok": false, "msg": …}`); a validation error
  keeps FastAPI's own JSON unless `json` is given. `api=`, `files=` as above;
  `app_name=` names the app on the plain page; `soft=` as above.

  The 500 answer comes from outside every middleware, so `install` dresses it
  itself: `no-store`, no framing, `nosniff` (harden.py's four).

  `await json_object(request)` → the body as a dict, or a 400 "Send a JSON
  object." — for a write that reads `request.json()` (a list, a number or no
  JSON at all was a 500 in museum, health, tv and vac).
"""

from __future__ import annotations

import html
import http
import inspect
import logging
import sys

API = ("/api/",)
FILES = ("/static/",)
SOFT = ("x-soft-nav",)

log = logging.getLogger("kit.errors")

# A heading and a sentence for each status a person meets. A route's own
# detail ("No such film.") replaces the sentence.
_WORDS = {
    400: ("That does not read", "The address or the form has something this page cannot use."),
    401: ("Sign in first", "This page needs the app's token."),
    403: ("Not allowed", "This was refused. A write from another site is never taken."),
    404: ("Not here", "There is no page at this address. It may have moved, or the link has a typo."),
    405: ("Nothing to see at this address", "It only takes what a button on a page sends. "
                                            "Go back to the page and press again."),
    409: ("That clashes", "Something changed in the meantime. Reload and try again."),
    410: ("Gone", "This was here once and has been removed."),
    413: ("Too big", "That is more than this app takes at once."),
    429: ("Too many at once", "Wait a minute and try again."),
}
_SERVER = ("Something broke on p340", "The page could not be made. Nothing was changed. "
                                      "Go back and try again in a minute.")


class Error:
    """What went wrong, in words for a page."""

    __slots__ = ("status", "title", "text", "detail", "fields")

    def __init__(self, status, title, text, detail=None, fields=()):
        self.status, self.title, self.text = status, title, text
        self.detail, self.fields = detail, tuple(fields)

    def __repr__(self):
        return f"Error({self.status}, {self.title!r}, {self.text!r})"


def _phrase(status):
    try:
        return http.HTTPStatus(status).phrase
    except ValueError:
        return "Error"


def describe(status, detail=None, method="GET", fields=()) -> Error:
    """The heading and sentence a page shows for `status`."""
    fields = tuple(str(f) for f in fields)
    if status >= 500:
        title, text = _SERVER
    elif status in (400, 422):
        named = f" ({', '.join(fields)})" if fields else ""
        if method in ("GET", "HEAD"):
            title, text = "That address does not read", f"It has a value this page cannot use{named}."
        else:
            title, text = ("That did not go through",
                           f"It was sent without something it needs{named}. Go back and try again.")
    else:
        title, text = _WORDS.get(status, ("That did not work", _phrase(status) + "."))
    if status < 500 and isinstance(detail, str) and detail.strip() and detail != _phrase(status):
        text = detail.strip()
        text = text[:1].upper() + text[1:] + ("" if text[-1] in ".!?" else ".")
    return Error(status, title, text, detail, fields)


def wants_page(method, path, headers, api=API, files=FILES, soft=SOFT) -> bool:
    """True when a person navigated here and should get a page."""
    if path.startswith(tuple(api)):
        return False
    if any(headers.get(h) for h in soft):
        return True
    mode = headers.get("sec-fetch-mode")
    if mode:
        return mode == "navigate"
    if method not in ("GET", "HEAD") or path.startswith(tuple(files)):
        return False
    return "text/html" in (headers.get("accept") or "")


def plain_page(err: Error, app="") -> str:
    """A whole HTML page for `err` that needs nothing from the app."""
    e = html.escape
    name = f"{e(app)} · " if app else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="color-scheme" content="dark light">
<title>{e(err.title)} · {name}{err.status}</title>
<style>
:root{{color-scheme:dark light;--bg:#0b0e14;--fg:#e6e9ef;--dim:#9aa7bb;--accent:#7aa2f7}}
@media (prefers-color-scheme:light){{:root{{--bg:#f6f4f2;--fg:#1d2330;--dim:#55606f;--accent:#2f5bd3}}}}
html,body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}}
main{{max-width:34rem;margin:0 auto;padding:max(15vh,4rem) 16px 2rem}}
p.code{{color:var(--dim);margin:0;font-size:.85rem;letter-spacing:.06em}}
h1{{font-size:1.4rem;margin:.2rem 0 .6rem}}
p{{color:var(--dim)}} a{{color:var(--accent)}}
nav{{display:flex;gap:1.5rem;margin-top:1.5rem}}
nav a{{min-height:44px;display:inline-flex;align-items:center}}
</style></head>
<body><main>
<p class="code">{name}{err.status}</p>
<h1>{e(err.title)}</h1>
<p>{e(err.text)}</p>
<nav><a href="/">Home</a><a href="https://p340.grining.eu/">p340 — all apps</a></nav>
</main></body></html>
"""


# --- Starlette / FastAPI ------------------------------------------------------

# The answer to an exception leaves through ServerErrorMiddleware, outside
# every middleware the app added (harden.py's, the gate's, caching.py's).
_DRESS = {
    "Cache-Control": "no-store",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
}


async def json_object(request) -> dict:
    """The request's JSON body when it is an object, else HTTPException(400)."""
    from starlette.exceptions import HTTPException
    try:
        body = await request.json()
    except (ValueError, UnicodeDecodeError, RecursionError):   # 100k-deep nesting: RecursionError
        raise HTTPException(400, "Send a JSON object.") from None
    if not isinstance(body, dict):
        raise HTTPException(400, "Send a JSON object.")
    return body


def install(app, page=None, *, api=API, files=FILES, json=None, app_name="", validation=None,
            soft=SOFT):
    """Register the kit's error handlers on a Starlette or FastAPI `app`."""
    from starlette.concurrency import run_in_threadpool
    from starlette.exceptions import HTTPException
    from starlette.responses import HTMLResponse, JSONResponse, Response

    async def call(fn, request, err):
        if inspect.iscoroutinefunction(fn):
            return await fn(request, err)
        return await run_in_threadpool(fn, request, err)

    async def as_page(request, err, headers=None):
        resp = None
        if page is not None:
            try:
                resp = await call(page, request, err)
            except Exception:
                log.exception("error page for %s %s failed", err.status, request.url.path)
        if resp is None:
            resp = HTMLResponse(plain_page(err, app_name))
        resp.status_code = err.status
        for k, v in (headers or {}).items():
            resp.headers[k] = v
        return resp

    async def answer(request, err, headers=None, default_json=None):
        if wants_page(request.method, request.url.path, request.headers, api, files, soft):
            return await as_page(request, err, headers)
        if json is not None:
            resp = await call(json, request, err)
            if resp is not None:
                for k, v in (headers or {}).items():
                    resp.headers[k] = v
                return resp
        if default_json is not None:
            return default_json
        return JSONResponse({"detail": err.detail if err.detail is not None else _phrase(err.status)},
                            status_code=err.status, headers=headers)

    async def http_error(request, exc):
        if request.scope["type"] != "http":
            raise exc
        headers = getattr(exc, "headers", None)
        if exc.status_code in (204, 304) or exc.status_code < 400:
            return Response(status_code=exc.status_code, headers=headers)
        return await answer(request, describe(exc.status_code, exc.detail, request.method), headers)

    async def too_big(request, exc):
        # An id or offset past SQLite's integers (`/e/99999999999999999999`).
        if request.scope["type"] != "http":
            raise exc
        if request.method in ("GET", "HEAD"):
            return await answer(request, describe(404, None, request.method))
        return await answer(request, describe(422, "That number is too big.", request.method))

    async def server_error(request, exc):
        if request.scope["type"] != "http":
            raise exc
        err = describe(500, None, request.method)
        if wants_page(request.method, request.url.path, request.headers, api, files, soft):
            resp = await as_page(request, err)
        else:
            resp = None
            if json is not None:
                try:
                    resp = await call(json, request, err)
                except Exception:
                    log.exception("error JSON for %s failed", request.url.path)
            if resp is None:
                resp = JSONResponse({"detail": "Internal Server Error"}, status_code=500)
        resp.status_code = 500
        for k, v in _DRESS.items():
            resp.headers[k] = v
        return resp

    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(OverflowError, too_big)
    app.add_exception_handler(Exception, server_error)

    async def respond(request, status, detail=None, fields=()):
        return await answer(request, describe(status, detail, request.method, fields))

    if validation is None:
        fx = sys.modules.get("fastapi.exceptions")
        if fx is None:
            return respond
        from fastapi.exception_handlers import request_validation_exception_handler
        validation = (fx.RequestValidationError, request_validation_exception_handler)
    exc_class, default_json = validation

    async def bad_params(request, exc):
        if request.scope["type"] != "http":
            raise exc
        fields = sorted({str(e["loc"][-1]) for e in exc.errors() if e.get("loc")})
        err = describe(422, None, request.method, fields)
        default = None
        if json is None and not wants_page(request.method, request.url.path, request.headers, api, files, soft):
            default = await default_json(request, exc)
        return await answer(request, err, None, default)

    app.add_exception_handler(exc_class, bad_params)
    return respond
