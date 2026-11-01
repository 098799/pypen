"""The pen list, /pens/ (owner and guests), paged on the server (kit §14, PYPEN-7).

It used to load all 126 pens with their photos and cut them into rotation
groups in Python. Now the group is a number in SQL (`GROUP_ORDER`: priority
0–3 of Tomek's rotation, the other active pens, the defunct ones), the rows
come 50 at a time in that order, and the rotation chips and the headings take
their counts from one grouped query over the same filter. A page that starts
inside a group (Load more, a bookmarked `?offset=`) does not repeat the
heading; `static/items/js/more.js` joins its rows to the group above.

Queries per page, whatever the number of rows: the grouped count, the rows
(with brand and rotation joined), their photos (one IN query).
"""

from django.db.models import Case, Count, F, IntegerField, Q, Value, When

from dpypen.items import listing
from dpypen.items.models import Pen

# (key, heading, chip). The chip bar is horizontal and lives on a 390px
# phone, where "Priority 0" spent ten characters saying what one says.
GROUPS = [
    ("p0", "Priority 0", "0"),
    ("p1", "Priority 1", "1"),
    ("p2", "Priority 2", "2"),
    ("p3", "Priority 3", "3"),
    ("other", "Other active", "Other"),
    ("defunct", "Defunct / sold", "Defunct"),
]
GROUP_ORDER = {key: n for n, (key, _, _) in enumerate(GROUPS)}
GROUP_BY_ORDER = {n: key for key, n in GROUP_ORDER.items()}
TITLES = {key: title for key, title, _ in GROUPS}


def _mine(n):
    return Q(rotation__in_use=True, rotation__whos="Tomek", rotation__priority=n)


def group_q(key):
    """The rows of one group, as a filter."""
    if key == "defunct":
        return Q(rotation__in_use=False)
    if key == "other":
        return Q(rotation__in_use=True) & ~Q(rotation__whos="Tomek", rotation__priority__in=[0, 1, 2, 3])
    return _mine(int(key[1]))


def group_case():
    """The group as its ordinal, in SQL."""
    return Case(
        When(rotation__in_use=False, then=Value(GROUP_ORDER["defunct"])),
        *[When(_mine(n), then=Value(n)) for n in range(4)],
        default=Value(GROUP_ORDER["other"]),
        output_field=IntegerField(),
    )


def filtered(request):
    """(queryset, q): every pen the search keeps, ordered, with the group."""
    q = (request.GET.get("q") or "").strip()
    qs = listing.search(Pen.objects.all(), q, listing.PEN_FIELDS).annotate(grp=group_case())
    return qs, q


def order(qs):
    return qs.order_by("grp", F("rotation__priority").asc(nulls_last=True), "brand__name", "model", "pk")


def build(request):
    """The template context for /pens/ (and the rows for /api/pens)."""
    limit, offset = listing.page_args(request)
    base, q = filtered(request)

    counts = {GROUP_BY_ORDER[r["grp"]]: r["n"] for r in base.order_by().values("grp").annotate(n=Count("pk"))}

    rot = (request.GET.get("rot") or "").strip()
    # `rot` is only honoured when it names a real group, so a stale ?rot= from
    # a bookmark falls back to showing everything — and "All" lights up on the
    # same condition.
    active_rot = rot if rot in GROUP_ORDER else ""
    qs = base.filter(group_q(active_rot)) if active_rot else base
    total = counts.get(active_rot, 0) if active_rot else sum(counts.values())

    rows, before = listing.window(order(qs.select_related("brand", "rotation").prefetch_related("photos")), offset, limit)
    for p in rows:
        photos = list(p.photos.all()[:1])
        p.first_photo = photos[0] if photos else None
        p.list_thumb_url = p.first_photo.grid_url if p.first_photo else None
        p.list_thumb_styled = bool(p.first_photo and p.first_photo.image_styled)
    prev = GROUP_BY_ORDER[before.grp] if before is not None else None
    listing.heads(rows, lambda p: GROUP_BY_ORDER[p.grp], prev if listing.is_more(request) else None)

    sections = listing.sections(rows)
    for s in sections:
        s["title"] = TITLES[s["key"]]
        s["count"] = counts.get(s["key"], 0)
        r = s["rows"][0].rotation
        s["subtitle"] = f"~every {r.how_often} days" if s["key"].startswith("p") else r.whos if s["key"] == "other" else ""

    def _url_with(**changes):
        params = request.GET.copy()
        for k, v in changes.items():
            if v is None:
                params.pop(k, None)
            else:
                params[k] = v
        params.pop("offset", None)
        qs_str = params.urlencode()
        return request.path + (("?" + qs_str) if qs_str else "")

    rot_filters = [{"key": "", "label": "All", "title": "All pens", "count": sum(counts.values()), "url": _url_with(rot=None), "on": not active_rot}]
    for key, title, chip in GROUPS:
        if counts.get(key):
            rot_filters.append({"key": key, "label": chip, "title": title, "count": counts[key], "url": _url_with(rot=key), "on": active_rot == key})

    view = "grid" if request.GET.get("view") == "grid" else "list"
    return {
        "pens": rows,
        "sections": sections,
        "headless": bool(active_rot),
        "rot_filters": rot_filters,
        "rot": active_rot,
        "query": q,
        "terms": listing.lists.tokens(q),
        "more": listing.more(request, offset, limit, total),
        "nav": "pens",
        "view": view,
        "list_url": _url_with(view=None),
        "grid_url": _url_with(view="grid"),
    }


def template_for(request, context):
    partial = listing.is_more(request) or (request.headers.get("HX-Request") and not request.headers.get("HX-Boosted"))
    if not partial:
        return "items/pens/list.html"
    return "items/pens/_grid_content.html" if context["view"] == "grid" else "items/pens/_list_content.html"


def item(p, request=None):
    """One pen in the JSON envelope."""
    return {
        "id": p.pk,
        "brand": p.brand.name,
        "model": p.model,
        "finish": p.finish or "",
        "filling": p.filling,
        "group": p.group,
        "priority": p.rotation.priority,
        "in_use": p.rotation.in_use,
        "obtained": p.obtained.isoformat() if p.obtained else None,
        "thumb": p.list_thumb_url,
        "url": f"/pens/{p.pk}/",
    }
