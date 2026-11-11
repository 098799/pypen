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
"""

import datetime
import os
import threading
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

        def make():
            response = self._make(request, base, shape)
            made.append(True)
            return response

        try:
            blob = memo.get(connection.settings_dict["NAME"], "page", make, *key, ttl=TTL)
        except _NotKept as e:
            e.response["X-Pypen-Memo"] = "skip"
            return e.response
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
