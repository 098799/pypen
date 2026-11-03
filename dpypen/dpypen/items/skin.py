"""One set of views, two faces (PYPEN-11).

The new version of the app lives under /next/. Everything that reads or writes
the collection is the same view on both addresses, so a rule (a login check, an
undo, a photo's clean-up) lands once. Only the page differs:

    render(request, "items/pens/form.html", ctx)   /pens/add/
    render(request, "next/pens/form.html", ctx)    /next/pens/add/

`rehome` puts a view on a /next/ address: a redirect the view answers to one of
its own pages stays in the new version.
"""

from functools import wraps

from django import shortcuts

PREFIX = "/next"
# The first part of each path that has a twin under /next/.
_MIRRORED = ("/pens/", "/inks/", "/usages/", "/import/", "/search/", "/settings/")


def is_next(request) -> bool:
    return request.path.startswith(PREFIX + "/")


def render(request, template, context=None, *args, **kwargs):
    context = {} if context is None else context
    if is_next(request):
        from dpypen.items.nextui import enrich

        template = "next/" + template.removeprefix("items/")
        context = enrich.apply(template, request, context)
    return shortcuts.render(request, template, context, *args, **kwargs)


def to_next(url: str) -> str:
    """The twin of an address, for one that has one."""
    if url.startswith(_MIRRORED):
        return PREFIX + url
    if url.startswith("/dashboard/"):
        return PREFIX + "/"
    if url.startswith("/pick/"):
        return PREFIX + url
    return url


def rehome(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        resp = view(request, *args, **kwargs)
        if resp.status_code in (301, 302, 303, 307) and "Location" in resp:
            resp["Location"] = to_next(resp["Location"])
        return resp

    return wrapped
