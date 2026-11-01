"""The lists as JSON, in the kit's one envelope (kit README §14, PYPEN-7):

    GET /api/pens    ?q= &rot= &limit= &offset=
    GET /api/inks    ?q= &color= &samples=1 &used=1 &sort= &limit= &offset=
    GET /api/usages  ?q= &state=active|past &limit= &offset=

    {"items": [...], "total": N, "limit": 50, "offset": 0}

Each takes the same parameters as its page and is built by the same code
(`penindex.build`, `inkindex.build`, `crud.usage_rows`), so the two cannot
disagree. `limit` is 1–100; more, or a bad offset, is a 422 (`listing.ListErrors`).
Owner and guests, like the pages; anyone else gets a 403. Not cached.
"""

from datetime import date

from django.http import JsonResponse
from django.views.decorators.http import require_safe

from dpypen.items import inkindex, listing, penindex
from dpypen.items.auth import active_invite


def _visible(request):
    return request.user.is_authenticated or active_invite(request) is not None


def _refuse():
    resp = JsonResponse({"detail": "Sign in, or open an invite link, to see this."}, status=403)
    resp["Cache-Control"] = "no-store"
    return resp


@require_safe
def pens(request):
    if not _visible(request):
        return _refuse()
    ctx = penindex.build(request)
    m = ctx["more"]
    return listing.json_page([penindex.item(p) for p in ctx["pens"]], m["total"], m["limit"], m["offset"])


@require_safe
def inks(request):
    if not _visible(request):
        return _refuse()
    ctx = inkindex.build(request, public=False)
    m = ctx["more"]
    return listing.json_page([inkindex.item(i) for i in ctx["inks"]], m["total"], m["limit"], m["offset"])


@require_safe
def usages(request):
    if not _visible(request):
        return _refuse()
    from dpypen.items.crud import usage_search

    limit, offset = listing.page_args(request)
    qs, _ = usage_search(request)
    state = request.GET.get("state", "")
    if state == "active":
        qs = qs.filter(end__isnull=True)
    elif state == "past":
        qs = qs.filter(end__isnull=False)
    total = qs.count()
    today = date.today()
    rows = list(qs.order_by("-begin", "-pk")[offset:offset + limit])
    items = [{
        "id": u.pk,
        "pen": {"id": u.pen_id, "label": str(u.pen), "url": f"/pens/{u.pen_id}/"},
        "ink": {"id": u.ink_id, "label": str(u.ink), "url": f"/inks/{u.ink_id}/"},
        "nib": str(u.nib),
        "begin": u.begin.isoformat(),
        "end": u.end.isoformat() if u.end else None,
        "days": ((u.end or today) - u.begin).days,
    } for u in rows]
    return listing.json_page(items, total, limit, offset)
