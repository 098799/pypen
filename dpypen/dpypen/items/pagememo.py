"""Whole pages kept until the database changes (speed pass, 11 Nov 2026).

Why: a signed-in page cost 30-160 ms of Python on bae (model objects and
template rendering; SQL is under 4 ms on every page), and the answer is the
same until something is written. One person uses the app, writes come a few
times a day, and a GET never writes (checked: `PRAGMA data_version` holds over
a crawl of every page). So the rendered answer is kept, with the kit's
`dbmemo.Memo`, until any commit to the database file, and a repeat visit costs
the session lookup and a dict hit (~1-3 ms).

What an answer is keyed by — everything the page can read:
  - the path and the whole query string;
  - the session key and the signed-in user (the session row is read on every
    request, so an expired or deleted session is never served a kept page);
  - every cookie but the session's (the CSRF cookie: a kept form's token
    belongs to that browser's secret);
  - today's date (pages count days), and a ttl as a safety net;
  - every request header the view read the last time this page was made
    (`Referer` for the Back link, htmx's `HX-Request`, Load more's
    `X-Pypen-More`): reads are recorded while a page is made, and a page
    whose render read a header the key did not carry is not kept; the next
    request carries it in the key. Same inputs, same page.

What is never kept: anything but a GET answered 200 with HTML or JSON, an
answer that sets a cookie, a page that showed or queued a flash message, a
request without a session cookie, a page with a CSRF token for a browser that
had no CSRF cookie yet (its token goes with the cookie this answer sets), and
the paths in SKIP.

One process holds one store (the service runs one gunicorn worker with
threads since this pass); with several workers each keeps its own.

Made again ahead of the request (`Warmer`): a write (any POST) empties the
store, and the first visit of each page after it paid the whole make again
(the desk ~80 ms on bae, Timeline ~150). After a POST answered below 400, a
thread waits a moment (the page the POST sends the browser to is made by that
request) and then makes again, one by one, the pages kept most recently (at
most WARM_MAX, used in the last WARM_AGE seconds), by replaying their request
through Django: same path, query, cookies and headers, so the same key. A GET
never writes, so a replay changes nothing; a session that ended answers a
redirect, which is never kept.
"""

import datetime
import io
import os
import sys
import threading
import time
from collections import OrderedDict

from django.db import connection
from django.http import HttpResponse
from django.http.request import HttpHeaders

from dpypen.items.dbmemo import Memo

TTL = 15 * 60
# PYPEN_PAGE_MEMO=0 in the secrets file turns it off (a restart): every page
# made again, as before the speed pass. For a suspected stale page, and for
# comparing made against kept on a spare port.
ON = os.getenv("PYPEN_PAGE_MEMO", "1") != "0"
SKIP = ("/admin/", "/accounts/", "/i/", "/undo/", "/kit/", "/sw.js", "/api/version", "/static/", "/media/")
TYPES = ("text/html", "application/json")

memo = Memo(max=160)

# (path, query, session, cookies) -> the META keys a page there was seen to
# read. Only grows (a read set from one branch joins one from another), so
# an alternating pair settles after one extra make.
_shapes: OrderedDict = OrderedDict()
_shapes_lock = threading.Lock()
_SHAPES_MAX = 512


WARM_MAX = 12
WARM_AGE = 2 * 3600
WARM_WAIT = 1.0  # seconds after the POST: its own redirect target comes first


class Warmer:
    """The pages to make again after a write, and the thread that does it."""

    def __init__(self):
        self._lock = threading.Lock()
        self._recipes: OrderedDict = OrderedDict()  # key -> (environ, last used)
        self._kick = threading.Event()
        self._thread = None
        self.handler = None  # the WSGI handler, made on first use
        self.made = 0  # pages made by replays (tests, the README's numbers)
        # Only for a database file: the memo keeps nothing for an in-memory
        # one (the test database), so there is nothing to make again.
        self.enabled = lambda: os.path.isfile(str(connection.settings_dict["NAME"]))

    def note(self, key, environ):
        """A kept page was asked for: keep how to ask for it again."""
        env = {k: v for k, v in environ.items() if isinstance(v, str)}
        with self._lock:
            self._recipes[key] = (env, time.monotonic())
            self._recipes.move_to_end(key)
            while len(self._recipes) > 4 * WARM_MAX:
                self._recipes.popitem(last=False)

    def kick(self):
        """A write happened: make the recent pages again, soon, off the request."""
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._loop, name="pagememo-warmer", daemon=True)
                self._thread.start()
        self._kick.set()

    def recent(self):
        now = time.monotonic()
        with self._lock:
            items = list(self._recipes.items())
        fresh = [(k, env) for k, (env, used) in reversed(items) if now - used < WARM_AGE]
        return fresh[:WARM_MAX]

    def run_once(self):
        """Replay the recent pages now (the thread's work; tests call it)."""
        from django.core.handlers.wsgi import WSGIHandler

        if self.handler is None:
            self.handler = WSGIHandler()
        for _key, env in self.recent():
            environ = dict(env)
            environ.update({
                "REQUEST_METHOD": "GET", "wsgi.input": io.BytesIO(b""), "wsgi.errors": sys.stderr,
                "wsgi.version": (1, 0), "wsgi.multithread": True, "wsgi.multiprocess": False,
                "wsgi.run_once": False, "wsgi.url_scheme": env.get("wsgi.url_scheme", "http"),
                "HTTP_X_PYPEN_WARM": "1",
            })
            try:
                result = self.handler(environ, lambda status, headers, exc_info=None: None)
                if hasattr(result, "close"):
                    result.close()
                self.made += 1
            except Exception as exc:  # a replay must never take the thread down
                print(f"pagememo warm {env.get('PATH_INFO')}: {exc!r}", file=sys.stderr)
            if self._kick.is_set():
                return  # another write came: start again from the top
            time.sleep(0.02)  # give a request the GIL between pages

    def _loop(self):
        while True:
            self._kick.wait()
            time.sleep(WARM_WAIT)
            self._kick.clear()
            try:
                self.run_once()
            except Exception as exc:
                print(f"pagememo warm: {exc!r}", file=sys.stderr)


warmer = Warmer()


class _NotKept(Exception):
    def __init__(self, response):
        self.response = response


class _ReadMeta(dict):
    """request.META that notes which keys were read."""

    def __init__(self, *a):
        super().__init__(*a)
        self.read = set()

    def __getitem__(self, k):
        self.read.add(k)
        return super().__getitem__(k)

    def get(self, k, default=None):
        self.read.add(k)
        return super().get(k, default)

    def __contains__(self, k):
        self.read.add(k)
        return super().__contains__(k)


class _ReadHeaders(HttpHeaders):
    """request.headers that notes reads in the META it came from."""

    def __init__(self, meta):
        super().__init__(dict(meta))
        self._meta = meta

    def __getitem__(self, key):
        name = key.upper().replace("-", "_")
        self._meta.read.add(name if name in self.UNPREFIXED_HEADERS else self.HTTP_PREFIX + name)
        return super().__getitem__(key)

    def __contains__(self, key):
        try:
            self[key]
        except KeyError:
            return False
        return True

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


# META keys that are the same on every request, or already in the key.
_FIXED = {
    "QUERY_STRING",
    "PATH_INFO",
    "SCRIPT_NAME",
    "REQUEST_METHOD",
    "HTTP_COOKIE",
    "CSRF_COOKIE",
    "CSRF_COOKIE_NEEDS_UPDATE",
    "SERVER_NAME",
    "SERVER_PORT",
    "HTTP_HOST",
    "HTTP_X_FORWARDED_PROTO",
    "wsgi.url_scheme",
}


def _skip(request):
    if request.method != "GET" or request.path.startswith(SKIP):
        return True
    c = request.COOKIES
    return "messages" in c or not c.get("sessionid")


def _meta_value(meta, k):
    v = dict.get(meta, k)
    return v if isinstance(v, (str, int, bool, type(None))) else repr(type(v))


class PageMemo:
    """Middleware, last in the list: the ones above still run on a kept page
    (headers, CSRF cookie refresh, list errors)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if ON and request.method == "POST":
            response = self.get_response(request)
            if response.status_code < 400 and warmer.enabled():
                warmer.kick()
            return response
        if not ON or _skip(request):
            return self.get_response(request)
        user = request.session.get("_auth_user_id")
        if not user:
            return self.get_response(request)
        cookies = tuple(sorted((k, v) for k, v in request.COOKIES.items() if k != "sessionid"))
        base = (request.path, request.META.get("QUERY_STRING", ""), request.session.session_key, user, cookies)
        with _shapes_lock:
            shape = _shapes.get(base, frozenset())
        key = base + (datetime.date.today().isoformat(), tuple((k, _meta_value(request.META, k)) for k in sorted(shape)))
        made = []
        environ = dict(request.META)  # before _make wraps it

        def make():
            response = self._make(request, base, shape)
            made.append(True)
            return response

        try:
            blob = memo.get(connection.settings_dict["NAME"], "page", make, *key, ttl=TTL)
        except _NotKept as e:
            e.response["X-Pypen-Memo"] = "skip"
            return e.response
        if not request.META.get("HTTP_X_PYPEN_WARM") and warmer.enabled():
            warmer.note(key, environ)
        return self._answer(request, blob, "miss" if made else "hit")

    def _make(self, request, base, shape):
        meta = _ReadMeta(request.META)
        request.META = meta
        request.__dict__["headers"] = _ReadHeaders(meta)
        response = self.get_response(request)
        read = {k for k in meta.read if k not in _FIXED}
        if not read <= shape:
            with _shapes_lock:
                _shapes[base] = frozenset(shape | read)
                _shapes.move_to_end(base)
                while len(_shapes) > _SHAPES_MAX:
                    _shapes.popitem(last=False)
            raise _NotKept(response)
        if not request.COOKIES.get("csrftoken") and "CSRF_COOKIE" in request.META:
            # The page made a CSRF secret for a browser that had none: its
            # token belongs to the cookie this answer sets, never to another.
            raise _NotKept(response)
        ctype = response.get("Content-Type", "")
        queued = getattr(getattr(request, "_messages", None), "_queued_messages", None)
        used = getattr(getattr(request, "_messages", None), "used", False)
        if response.status_code != 200 or response.streaming or response.cookies or queued or used or not ctype.startswith(TYPES):
            raise _NotKept(response)
        headers = [(k, v) for k, v in response.items() if k.lower() not in ("content-length", "x-pypen-memo")]
        return (response.content, headers, bool(request.META.get("CSRF_COOKIE_NEEDS_UPDATE")))

    def _answer(self, request, blob, how):
        content, headers, csrf = blob
        response = HttpResponse(content)
        for k, v in headers:
            response[k] = v
        if csrf:
            # The page carries a token: refresh the cookie as a made page would.
            request.META["CSRF_COOKIE_NEEDS_UPDATE"] = True
        response["X-Pypen-Memo"] = how
        return response
