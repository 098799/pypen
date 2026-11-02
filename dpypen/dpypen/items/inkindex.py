"""The ink index — one cupboard, one toolbar, two doors.

`/inks/` (owner and invited guests) and `/pub/inks/` (anyone at all) render the
same inks through the same filter bar, so the two have to agree about what the
controls do. They did not. The public route was a stripped fork of the private
one that had drifted, and the toolbar it rendered was mostly scenery:

* every colour chip came out as `href="" hx-get=""`, because the fork built
  `color_chips` without the `url` key `_filters.html` reads — so the page whose
  own subtitle says "browse by colour" could not browse by colour;
* `clear_url` was missing the same way, so Clear was dead too;
* the sort `<select>` rendered with no options at all;
* the search box's `hx-get` was hardcoded to `{% url 'inks_list' %}`, so typing
  in the public cupboard fired a request at the *private* route, which 302s to
  Google, which htmx cannot follow cross-origin. It failed silently.

Deriving every URL from `request.path` is what makes one implementation serve
both routes: a control can only ever set or clear its own key, on whichever
path the visitor is actually standing.

The one real difference is where an ink links to. Signed in, that is
`/inks/<pk>/`. Anonymous, it has to be the ink's own share token — `/inks/<pk>/`
is login-gated, so the public grid used to be a wall of links that bounced the
visitor to Google.
"""

from django.db.models import Case, Count, F, IntegerField, OuterRef, Subquery, Value, When
from django.db.models.functions import Coalesce

from dpypen.items import listing
from dpypen.items.models import Ink, Usage
from dpypen.items.public import INK_COLOR_HEX

# "Colour" keeps the grouped-by-hue page that the colour chips navigate. Every
# other order is a flat list: "newest first", split into sixteen colour
# sections, is not newest first in any useful sense. Each order ends on the
# primary key, so a row never shows on two pages (kit §14).
SORTS = {
    "color":  ("Colour",     ("hue", "used_up", "brand__name", "name", "pk")),
    "brand":  ("Brand",      ("used_up", "brand__name", "name", "pk")),
    "new":    ("Newest",     ("used_up", F("obtained").desc(nulls_last=True), "brand__name", "pk")),
    "inked":  ("Most inked", ("used_up", "-n_usages", "brand__name", "pk")),
    "volume": ("Volume",     ("used_up", "-volume", "brand__name", "pk")),
}
COLORS = list(INK_COLOR_HEX)


def hue_case():
    """The colour as its place in INK_COLOR_HEX, in SQL; a colour not in the
    table goes last (the Python grouping this replaced dropped such inks)."""
    return Case(*[When(color=c, then=Value(n)) for n, c in enumerate(COLORS)],
                default=Value(len(COLORS)), output_field=IntegerField())


def n_usages():
    """How often an ink was inked, as a subquery: no join, no GROUP BY."""
    return Coalesce(Subquery(
        Usage.objects.filter(ink=OuterRef("pk")).order_by().values("ink")
        .annotate(n=Count("pk")).values("n")[:1]), 0)


def filtered(request):
    """(queryset without the colour filter, q, the switches)."""
    include_samples = request.GET.get("samples") == "1"
    include_used = request.GET.get("used") == "1"
    q = (request.GET.get("q") or "").strip()
    qs = Ink.objects.all()
    if not include_samples:
        qs = qs.filter(volume__gt=5)
    if not include_used:
        qs = qs.exclude(used_up=True)
    qs = listing.search(qs, q, listing.INK_FIELDS)
    return qs, q, include_samples, include_used


def build(request, *, public):
    """Return the template context for the ink index on `request.path`."""
    limit, offset = listing.page_args(request)
    base, q, include_samples, include_used = filtered(request)
    color_filter = request.GET.get("color", "")
    if color_filter not in INK_COLOR_HEX:
        color_filter = ""

    sort = request.GET.get("sort") or "color"
    if sort not in SORTS:
        sort = "color"

    # One grouped query: the chips' counts, the headings' counts and the total.
    # It reuses the list's own filter (samples, used up, the search), all but
    # the colour, so a chip says how many it would show.
    color_counts = dict(base.order_by().values_list("color").annotate(n=Count("pk")))
    qs = base.filter(color=color_filter) if color_filter else base
    total = color_counts.get(color_filter, 0) if color_filter else sum(color_counts.values())

    qs = qs.select_related("brand", "rotation").annotate(hue=hue_case())
    if sort == "inked":
        qs = qs.annotate(n_usages=n_usages())
    rows, before = listing.window(qs.order_by(*SORTS[sort][1]), offset, limit)
    for i in rows:
        i.hex = INK_COLOR_HEX.get(i.color, "#333")
        i.bg = i.swatch_bg

    if sort == "color":
        listing.heads(rows, lambda i: i.color,
                      before.color if (before is not None and listing.is_more(request)) else None)
    else:
        listing.heads(rows, lambda i: "all", "all" if listing.is_more(request) else None)
    sections = listing.sections(rows)
    for s in sections:
        s["flat"] = sort != "color"
        s["color"] = s["key"]
        s["hex"] = INK_COLOR_HEX.get(s["key"], "#333")
        s["count"] = color_counts.get(s["key"], 0)

    # These URLs were each spelled out by hand, here and in the templates, and
    # every spelling listed the params it happened to remember — so the colour
    # chips dropped ?q= and the view toggle dropped anything typed since the
    # page rendered. Deriving them from the live query string means a control
    # can only ever set or clear its own key. Any change starts at the first
    # row again (no ?offset=).
    def _url_with(**changes):
        params = request.GET.copy()
        for k, v in changes.items():
            if v:
                params[k] = v
            else:
                params.pop(k, None)
        params.pop("offset", None)
        qs_str = params.urlencode()
        return request.path + (("?" + qs_str) if qs_str else "")

    color_chips = [
        {"color": c, "hex": INK_COLOR_HEX[c], "count": color_counts.get(c, 0),
         "url": _url_with(color=None if color_filter == c else c)}
        for c in COLORS
        if color_counts.get(c, 0) > 0 or c == color_filter
    ]

    view = "grid" if request.GET.get("view") == "grid" else "list"
    filters = {
        "include_samples": include_samples,
        "include_used": include_used,
        "color": color_filter,
        "q": q,
        "terms": listing.lists.tokens(q),
        "color_chips": color_chips,
        "toggle_samples_url": _url_with(samples="1" if not include_samples else None),
        "toggle_used_url": _url_with(used="1" if not include_used else None),
        "clear_url": _url_with(samples=None, used=None, color=None, q=None),
        # The empty block (templates/items/inks/_empty_state.html): "Show all"
        # turns the hidden samples and used-up inks on, and an empty cupboard
        # is told apart from a filter that hides every ink.
        "show_all_url": _url_with(samples="1", used="1", color=None, q=None),
        "cupboard_empty": not rows and not Ink.objects.exists(),
        "view": view,
        "list_url": _url_with(view=None),
        "grid_url": _url_with(view="grid"),
        # htmx appends the form's own `q` to this, so it must carry every
        # *other* live param and nothing else — hardcoding a route here is
        # what sent the public cupboard's search to the private one.
        "search_url": _url_with(q=None),
        "sort": sort,
        "sort_label": SORTS[sort][0],
        "sort_options": [
            {"key": k, "label": v[0], "on": k == sort,
             "url": _url_with(sort=None if k == "color" else k)}
            for k, v in SORTS.items()
        ],
    }

    return {
        "inks": rows,
        "sections": sections,
        "filters": filters,
        "more": listing.more(request, offset, limit, total),
        "public": public,
        "nav": "pub_inks" if public else "inks",
    }


def item(i):
    """One ink in the JSON envelope."""
    return {
        "id": i.pk,
        "brand": i.brand.name,
        "line": i.line or "",
        "name": i.name,
        "color": i.color,
        "hex": i.hex,
        "volume": i.volume,
        "used_up": bool(i.used_up),
        "obtained": i.obtained.isoformat() if i.obtained else None,
        "url": f"/inks/{i.pk}/",
    }


def template_for(request, context):
    """List, grid or full page — the same choice on both routes."""
    partial = listing.is_more(request) or (
        request.headers.get("HX-Request") and not request.headers.get("HX-Boosted"))
    if not partial:
        return "items/inks/list.html"
    return "items/inks/_grid.html" if context["filters"]["view"] == "grid" else "items/inks/_content.html"
