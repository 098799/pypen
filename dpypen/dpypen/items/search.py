from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import render

from dpypen.items.auth import login_or_guest_required
from dpypen.items.models import Ink, Pen, Usage
from dpypen.items.public import INK_COLOR_HEX


SORTS = {
    "alpha": "alphabetical",
    "recent": "recently obtained",
    "used": "most used",
}
TYPES = {"both": "both", "pens": "pens", "inks": "inks"}


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

    pens = []
    inks = []
    terms = [t for t in q.split() if t]

    if q and type_ in ("both", "pens"):
        pqs = Pen.objects.select_related("brand", "rotation").prefetch_related("photos")
        for term in terms:
            pqs = pqs.filter(
                Q(brand__name__icontains=term)
                | Q(model__icontains=term)
                | Q(finish__icontains=term)
                | Q(filling__icontains=term)
                | Q(obtained_from__icontains=term)
            )
        if not show_defunct:
            pqs = pqs.filter(rotation__in_use=True)
        if sort == "alpha":
            pqs = pqs.order_by("brand__name", "model")
        elif sort == "recent":
            pqs = pqs.order_by("-obtained")
        elif sort == "used":
            pqs = pqs.annotate(
                total_days=Coalesce(Sum("usage__id"), 0) + Count("usage"),
            ).order_by("-total_days")
        pens = list(pqs[:60])
        for p in pens:
            photos = list(p.photos.all()[:1])
            if photos:
                ph = photos[0]
                p.thumb_url = ph.image_styled.url if ph.image_styled else (ph.thumbnail.url if ph.thumbnail else ph.image.url)
            else:
                p.thumb_url = None

    if q and type_ in ("both", "inks"):
        iqs = Ink.objects.select_related("brand")
        for term in terms:
            iqs = iqs.filter(
                Q(brand__name__icontains=term)
                | Q(name__icontains=term)
                | Q(line__icontains=term)
                | Q(color__icontains=term)
                | Q(obtained_from__icontains=term)
            )
        if not show_used_up:
            iqs = iqs.exclude(used_up=True)
        if not show_samples:
            iqs = iqs.filter(volume__gt=5)
        if sort == "alpha":
            iqs = iqs.order_by("brand__name", "name")
        elif sort == "recent":
            iqs = iqs.order_by("-obtained")
        elif sort == "used":
            iqs = iqs.annotate(fill_count=Count("usage")).order_by("-fill_count")
        inks = list(iqs[:60])
        for i in inks:
            i.hex = INK_COLOR_HEX.get(i.color, "#333")
            i.bg = i.swatch_bg

    def _toggle_url(key, new_val):
        params = request.GET.copy()
        if new_val:
            params[key] = new_val
        else:
            params.pop(key, None)
        q_ = params.urlencode()
        return request.path + (("?" + q_) if q_ else "")

    filters = {
        "query": q,
        "type": type_,
        "sort": sort,
        "show_defunct": show_defunct,
        "show_used_up": show_used_up,
        "show_samples": show_samples,
        "sorts": SORTS,
        "types": TYPES,
        "toggle_defunct_url": _toggle_url("defunct", "1" if not show_defunct else ""),
        "toggle_used_up_url": _toggle_url("used_up", "1" if not show_used_up else ""),
        "toggle_samples_url": _toggle_url("samples", "1" if not show_samples else ""),
    }

    context = {
        "query": q,
        "terms": terms,
        "pens": pens,
        "inks": inks,
        "filters": filters,
        "nav": "search",
    }
    partial = request.headers.get("HX-Request") and not request.headers.get("HX-Boosted")
    template = "items/_search_results.html" if partial else "items/search.html"
    return render(request, template, context)
