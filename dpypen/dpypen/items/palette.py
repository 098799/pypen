"""Command-palette endpoint for the keyboard layer (Ctrl-K, `d`).

Returns the grouped shape that ~/apps/kit/snippets/keys.html reads:

    {"groups": [{"type", "title", "items": [{"t", "s", "u"}, …],
                 "more": {"t", "u"}?}, …]}

A few rows per group and a "show all" row that lands on /search/ when there is
more. With nothing typed the layer shows the pages and the recent searches and
does not call this at all.
"""

from urllib.parse import quote

from django.http import JsonResponse

from dpypen.items import listing
from dpypen.items.auth import active_invite
from dpypen.items.models import Ink, Pen

LIMIT = 6


def _visible(request):
    return request.user.is_authenticated or active_invite(request) is not None


def palette(request):
    if not _visible(request):
        return JsonResponse({"groups": []}, status=403)

    q = (request.GET.get("q") or "").strip()
    if not listing.lists.tokens(q):
        return JsonResponse({"groups": []})

    # The kit's words (kit §14, PYPEN-7): every word must match, accents
    # fold ("zur" finds "Zürich"), the same fields as the lists and /search/.
    # It took the whole query as one phrase before, so "pilot blue" found
    # nothing.
    pens = listing.search(Pen.objects.select_related("brand", "rotation"), q,
                          listing.PEN_FIELDS).order_by("brand__name", "model", "pk")
    inks = listing.search(Ink.objects.select_related("brand"), q,
                          listing.INK_FIELDS).order_by("brand__name", "name", "pk")

    def group(type_, title, rows, total, search_type):
        g = {"type": type_, "title": title, "items": rows}
        if total > len(rows):
            g["more"] = {
                "t": f"Show all {title.lower()} matching",
                # the palette looks at everything, so the search must too
                "u": f"/search/?q={quote(q)}&type={search_type}"
                     "&defunct=1&used_up=1&samples=1",
            }
        return g

    pen_list = list(pens[:LIMIT + 1])
    ink_list = list(inks[:LIMIT + 1])
    pen_rows = [{
        "t": f"{p.brand.name} {p.model}" + (f" {p.finish}" if p.finish else ""),
        "s": p.filling or "",
        "u": f"/pens/{p.pk}/",
    } for p in pen_list[:LIMIT]]
    ink_rows = [{
        "t": f"{i.brand.name} " + (f"{i.line} " if i.line else "") + i.name,
        "s": i.color or "",
        "u": f"/inks/{i.pk}/",
    } for i in ink_list[:LIMIT]]

    groups = []
    if pen_rows:
        groups.append(group("pen", "Pens", pen_rows, len(pen_list), "pens"))
    if ink_rows:
        groups.append(group("ink", "Inks", ink_rows, len(ink_list), "inks"))
    return JsonResponse({"groups": groups})
