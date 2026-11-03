from django.db.models import Count, F, OuterRef, Subquery
from django.db.models.functions import Coalesce

from dpypen.items.skin import render
from dpypen.items import listing
from dpypen.items.auth import login_or_guest_required
from dpypen.items.models import Ink, Pen, Usage
from dpypen.items.public import INK_COLOR_HEX


SORTS = {
    "alpha": "alphabetical",
    "recent": "recently obtained",
    "used": "most used",
}
TYPES = {"both": "both", "pens": "pens", "inks": "inks"}


# Both kinds at once show this many of each, with Load more going on to that
# kind alone; one kind shows the usual page of 50.
PREVIEW = 20


def _n_usages(fk):
    """How many inkings a pen or an ink had, as a subquery (no GROUP BY).
    The "most used" order summed the inkings' ids before (PYPEN-7)."""
    return Coalesce(Subquery(
        Usage.objects.filter(**{fk: OuterRef("pk")}).order_by().values(fk)
        .annotate(n=Count("pk")).values("n")[:1]), 0)


PEN_ORDER = {
    "alpha": ("brand__name", "model", "pk"),
    "recent": ("-obtained", "pk"),
    "used": ("-n_used", "brand__name", "model", "pk"),
}
INK_ORDER = {
    "alpha": ("brand__name", "name", "pk"),
    "recent": (F("obtained").desc(nulls_last=True), "pk"),
    "used": ("-n_used", "brand__name", "name", "pk"),
}


def _more(request, kind, offset, limit, total, type_):
    """listing.more, but from both kinds Load more goes on with this kind alone."""
    m = listing.more(request, offset, limit, total)
    if m["next"] and type_ == "both":
        params = request.GET.copy()
        params["type"] = kind
        params["offset"] = str(offset + limit)
        params.pop("limit", None)
        m["next"] = request.path + "?" + params.urlencode()
    return m


@login_or_guest_required
def search(request):
    q = (request.GET.get("q") or "").strip()
    type_ = request.GET.get("type", "both")
    if type_ not in TYPES:
        type_ = "both"
    sort = request.GET.get("sort", "alpha")
    if sort not in SORTS:
        sort = "alpha"
    show_defunct = request.GET.get("defunct") == "1"
    show_used_up = request.GET.get("used_up") == "1"
    show_samples = request.GET.get("samples") == "1"
    limit, offset = listing.page_args(request, default=PREVIEW if type_ == "both" else listing.LIMIT_DEFAULT)
    if type_ == "both":
        offset = 0

    pens = inks = []
    pen_more = ink_more = None
    terms = listing.lists.tokens(q)

    if terms and type_ in ("both", "pens"):
        pqs = listing.search(Pen.objects.select_related("brand", "rotation"), q, listing.PEN_FIELDS)
        if not show_defunct:
            pqs = pqs.filter(rotation__in_use=True)
        total = pqs.count()
        if sort == "used":
            pqs = pqs.annotate(n_used=_n_usages("pen"))
        pens = list(pqs.prefetch_related("photos").order_by(*PEN_ORDER[sort])[offset:offset + limit])
        for p in pens:
            photos = list(p.photos.all()[:1])
            p.thumb_url = photos[0].grid_url if photos else None
        pen_more = _more(request, "pens", offset, limit, total, type_)

    if terms and type_ in ("both", "inks"):
        iqs = listing.search(Ink.objects.select_related("brand"), q, listing.INK_FIELDS)
        if not show_used_up:
            iqs = iqs.exclude(used_up=True)
        if not show_samples:
            iqs = iqs.filter(volume__gt=5)
        total = iqs.count()
        if sort == "used":
            iqs = iqs.annotate(n_used=_n_usages("ink"))
        inks = list(iqs.order_by(*INK_ORDER[sort])[offset:offset + limit])
        for i in inks:
            i.hex = INK_COLOR_HEX.get(i.color, "#333")
            i.bg = i.swatch_bg
        ink_more = _more(request, "inks", offset, limit, total, type_)

    def _toggle_url(key, new_val):
        params = request.GET.copy()
        if new_val:
            params[key] = new_val
        else:
            params.pop(key, None)
        params.pop("offset", None)
        q_ = params.urlencode()
        return request.path + (("?" + q_) if q_ else "")

    def _show_all_url():
        params = request.GET.copy()
        for key in ("defunct", "used_up", "samples"):
            params[key] = "1"
        params.pop("offset", None)
        return request.path + "?" + params.urlencode()

    filters = {
        "query": q,
        "type": type_,
        "sort": sort,
        "show_defunct": show_defunct,
        "show_used_up": show_used_up,
        "show_samples": show_samples,
        "sorts": SORTS,
        "types": TYPES,
        "any_hidden": (type_ != "inks" and not show_defunct)
                      or (type_ != "pens" and not (show_used_up and show_samples)),
        # The no-match block's ways out (templates/items/_search_results.html).
        "clear_url": _toggle_url("q", ""),
        "show_all_url": _show_all_url(),
        "toggle_defunct_url": _toggle_url("defunct", "1" if not show_defunct else ""),
        "toggle_used_up_url": _toggle_url("used_up", "1" if not show_used_up else ""),
        "toggle_samples_url": _toggle_url("samples", "1" if not show_samples else ""),
    }

    context = {
        "query": q,
        "terms": terms,
        "pens": pens,
        "inks": inks,
        "pen_more": pen_more,
        "ink_more": ink_more,
        "type": type_,
        "more_only": listing.is_more(request),
        "filters": filters,
        "nav": "search",
    }
    partial = listing.is_more(request) or (
        request.headers.get("HX-Request") and not request.headers.get("HX-Boosted"))
    template = "items/_search_results.html" if partial else "items/search.html"
    return listing.vary(render(request, template, context))
