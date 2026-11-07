"""The kit's snippets as cached files, not inline in every page (kit README §5.9).

shell.py is the byte copy of ~/apps/kit/py/shell.py (KIT-SHELL; fleet-check
`kit`); never edit it. This module names the files and serves them from a
view (`shell.answer`, Django is not ASGI here). The templates/items/_<snippet>
files stay the kit's byte copies.

Before: every page carried 60-190 KB of the snippets' style, script and header
comments again (the 404 page for a stranger was 193 KB), and no cache could
keep it (a page is `no-cache`).

The prefix is /kit/, not /static/: nginx on bae serves /static/ from
/var/www/pen-static and would never ask Django. The worker keeps /kit/ files
for offline like /static/ (pwa.KITSW["files"]).

Files, in the order the pages had the snippets:
  theme.js           blocking in <head>, after window.KITTHEME (_theme_boot.html)
  shell.css/.js      both shells: the layer, toast, empty, filters, update,
                     pull to refresh
  member.css/.js     both shells, the owner and guests only (as before): What's
                     new, the install bar, Settings' rows, the tab bar (KIT-TABS;
                     a stranger has no bar)
  wall.css/.js       the public walls: pull to refresh, update, filters
  tabs.css/.js       the walls, the owner and guests only: the tab bar

The scripts are NOT `defer`: the shells' own inline scripts (_shell_early,
_shell_behave, the What's new repaint, the settings page) call kitToast,
kitEmpty, kitLayer and kitSettings as they run. So each file loads blocking
where its first snippet was (the top of <body>), with the config objects
(KITUPDATE, WHATSNEW, KITINSTALL) inline before it. Kept a year at its ?v=,
it costs one fetch per deploy.
"""

from pathlib import Path

from django.http import Http404, HttpResponse

from . import shell

TEMPLATES = Path(__file__).resolve().parent / "templates" / "items"

KIT = shell.Shell(TEMPLATES, prefix="/kit")
KIT.js("theme.js", "_theme.js")
SHELL = ("_toast.html", "_empty.html", "_filters.html", "_update.html", "_pullrefresh.html")
KIT.css("shell.css", *SHELL)
# The layer first: its popstate listener before htmx's and the app's.
KIT.js("shell.js", "_layer.js", *SHELL)
# _settings.html sat inside #main on the settings page; its rows exist for the
# owner and guests only, and its script takes the browser's install offer, which
# a stranger's page must keep.
# The tab bar (_tabs.html) is drawn for them only too (_tabbar.html); its script
# mounts the nav at DOMContentLoaded, so it may load before the nav's markup.
MEMBER = ("_whatsnew.html", "_install.html", "_settings.html", "_tabs.html")
KIT.css("member.css", *MEMBER)
KIT.js("member.js", *MEMBER)
WALL = ("_pullrefresh.html", "_update.html", "_filters.html")
KIT.css("wall.css", *WALL)
KIT.js("wall.js", *WALL)
# A wall's tab bar, for the owner and guests (most of a wall's audience is signed out).
KIT.css("tabs.css", "_tabs.html")
KIT.js("tabs.js", "_tabs.html")


def url(name: str) -> str:
    """/kit/<name>?v=<hash> for a template (the `kit_shell` tag)."""
    return KIT.url(name)


def serve(request, name):
    """GET and HEAD of /kit/<name>: 304 on a known ETag, gzip made once,
    immutable at the current ?v= (shell.answer)."""
    if request.method not in ("GET", "HEAD"):
        raise Http404
    headers = {k.lower(): v for k, v in request.headers.items()}
    got = KIT.answer(request.path, request.META.get("QUERY_STRING", ""), headers)
    if got is None:
        raise Http404
    status, out, body = got
    resp = HttpResponse(b"" if request.method == "HEAD" else body, status=status,
                        content_type=KIT.files[name][1])
    for k, v in out:
        resp[k] = v
    return resp
