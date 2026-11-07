"""One set of views, two faces (PYPEN-11).

The new version took the main addresses in Nov 2026; the old one lives on
under /prev/. Everything that reads or writes the collection is the same view
on both addresses, so a rule (a login check, an undo, a photo's clean-up)
lands once. Only the page differs:

    render(request, "items/pens/form.html", ctx)   /prev/pens/add/
    render(request, "next/pens/form.html", ctx)    /pens/add/

The old views redirect by their old names, which are /prev/ addresses now.
`rehome` puts a view on a main address: a redirect it answers to one of its
own pages stays in the new version.
"""

from functools import wraps

from django import shortcuts

PREFIX = "/prev"
# The first part of each path that has a twin under /prev/.
_MIRRORED = ("/pens/", "/inks/", "/usages/", "/import/", "/search/", "/settings/", "/pick/", "/dashboard/")


def is_next(request) -> bool:
    """The new face: every address but the old version's."""
    return not is_prev(request.path)


def is_prev(path: str) -> bool:
    return path == PREFIX or path.startswith(PREFIX + "/")


def render(request, template, context=None, *args, **kwargs):
    context = {} if context is None else context
    if is_next(request):
        from dpypen.items.nextui import enrich

        template = "next/" + template.removeprefix("items/")
        context = enrich.apply(template, request, context)
    return shortcuts.render(request, template, context, *args, **kwargs)


def to_next(url: str) -> str:
    """The new twin of an old address, for one that has one."""
    if url.startswith(PREFIX + "/"):
        rest = url[len(PREFIX):]
        if rest.startswith(_MIRRORED):
            return rest
        if rest.startswith(("/samples/", "/swatches/")):
            return ("/usages" if rest.startswith("/samples/") else "/inks") + rest
    return url



def rehome(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        resp = view(request, *args, **kwargs)
        if resp.status_code in (301, 302, 303, 307) and "Location" in resp:
            resp["Location"] = to_next(resp["Location"])
        return resp

    return wrapped
