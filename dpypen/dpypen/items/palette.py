"""Command-palette endpoint for the keyboard layer (`d` opens it).

Returns the shape webkit's snippets/keys.html expects:

    {"items": [{"k": kind, "t": title, "s": subtitle, "u": url}, …]}

Kept deliberately small and un-paginated: the whole collection is 126 pens and
136 inks, so a query is a couple of indexed LIKEs and the result is capped well
below anything worth streaming.
"""

from django.db.models import Q
from django.http import JsonResponse

from dpypen.items.auth import active_invite
from dpypen.items.models import Ink, Pen

LIMIT = 40


def _visible(request):
    return request.user.is_authenticated or active_invite(request) is not None


def palette(request):
    if not _visible(request):
        return JsonResponse({"items": []}, status=403)

    q = (request.GET.get("q") or "").strip()
    items = []

    pens = Pen.objects.select_related("brand", "rotation")
    inks = Ink.objects.select_related("brand")
    if q:
        pens = pens.filter(
            Q(model__icontains=q) | Q(brand__name__icontains=q) | Q(finish__icontains=q)
        )
        inks = inks.filter(
            Q(name__icontains=q) | Q(brand__name__icontains=q) | Q(line__icontains=q)
        )

    for p in pens.order_by("brand__name", "model")[:LIMIT]:
        items.append({
            "k": "pen",
            "t": f"{p.brand.name} {p.model}" + (f" {p.finish}" if p.finish else ""),
            "s": p.filling or "",
            "u": f"/pens/{p.pk}/",
        })
    for i in inks.order_by("brand__name", "name")[:LIMIT]:
        items.append({
            "k": "ink",
            "t": f"{i.brand.name} {i.name}",
            "s": i.color or "",
            "u": f"/inks/{i.pk}/",
        })

    # Without a query the palette is a launcher, not a dump of the collection.
    if not q:
        items = items[:12]

    return JsonResponse({"items": items})
