"""Error pages in the app's chrome (kit README §4 "404 / errors", §5.7).

The kit's errors.py (KIT-ERRORS, a byte copy next to this file) is written
for FastAPI and Starlette; its stdlib half is what pypen takes: `describe()`
(the heading and the sentence a person reads for a status) and `wants_page()`
(a person navigated here, or an hx-boost swap asked: the page; a fetch, an
<img>, /api/ and the JSON files: JSON). Django calls the handlers below
(handler404/500/403/400 in dpypen/urls.py, CSRF_FAILURE_VIEW in settings);
with DEBUG on it shows its own debug pages instead.

- A 4xx page is the shell: the tab bar, the menu, a way on (Back, and the
  desk or the front page). A stranger gets the stranger's shell, so it never
  shows a count of anything.
- The 500 page needs nothing that may be what broke (the database the
  shell's context reads, the static manifest): a page of its own, in the
  paper colours, `no-store`.
- htmx does not swap a 4xx/5xx answer; the shell's htmx:beforeSwap hook takes
  these pages for a boosted navigation, so a dead link shows this page
  instead of doing nothing.
"""

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import loader

from dpypen.items import errors

API = ("/api/", "/whatsnew.json", "/manifest.json")
FILES = ("/static/", "/media/")
SOFT = ("hx-boosted",)

# The kit's 500 heading names p340; pypen runs on bae.
SERVER = ("Something broke", "The page could not be made. Nothing was changed. "
                             "Go back and try again in a minute.")
CSRF_TEXT = ("The form was open too long, or it came from another page. "
             "Go back, reload the page and send it again.")


def _wants_page(request):
    return errors.wants_page(request.method, request.path, request.headers,
                             api=API, files=FILES, soft=SOFT)


def _json(err):
    resp = JsonResponse({"detail": err.text}, status=err.status)
    resp["Cache-Control"] = "no-store"
    return resp


def _page(request, err):
    if not _wants_page(request):
        return _json(err)
    resp = render(request, "items/error.html", {"err": err, "nav": ""}, status=err.status)
    resp["Cache-Control"] = "no-store"
    return resp


def not_found(request, exception=None):
    return _page(request, errors.describe(404, method=request.method))


def forbidden(request, exception=None):
    return _page(request, errors.describe(403, method=request.method))


def bad_request(request, exception=None):
    return _page(request, errors.describe(400, method=request.method))


def csrf_failure(request, reason=""):
    err = errors.describe(403, method=request.method)
    err.title, err.text = "That did not go through", CSRF_TEXT
    return _page(request, err)


def server_error(request):
    err = errors.describe(500, method=request.method)
    err.title, err.text = SERVER
    if not _wants_page(request):
        return _json(err)
    try:
        body = loader.get_template("items/error_500.html").render({"err": err})
    except Exception:  # the page must not need what broke
        body = errors.plain_page(err, "Pens")
    resp = HttpResponse(body, status=500)
    resp["Cache-Control"] = "no-store"
    return resp
