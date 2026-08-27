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

from django.db.models import Count, F, Q

from dpypen.items.models import Ink
from dpypen.items.public import INK_COLOR_HEX

# "Colour" keeps the grouped-by-hue page that the colour chips navigate. Every
# other order is a flat list: "newest first", split into sixteen colour
# sections, is not newest first in any useful sense.
SORTS = {
    "color":  ("Colour",     ("used_up", "brand__name", "name")),
    "brand":  ("Brand",      ("used_up", "brand__name", "name")),
    "new":    ("Newest",     ("used_up", F("obtained").desc(nulls_last=True), "brand__name")),
    "inked":  ("Most inked", ("used_up", "-n_usages", "brand__name")),
    "volume": ("Volume",     ("used_up", "-volume", "brand__name")),
}


def build(request, *, public):
    """Return the template context for the ink index on `request.path`."""
    include_samples = request.GET.get("samples") == "1"
    include_used = request.GET.get("used") == "1"
    color_filter = request.GET.get("color", "")
    q = (request.GET.get("q") or "").strip()

    qs = Ink.objects.select_related("brand", "rotation")
    if not include_samples:
        qs = qs.filter(volume__gt=5)
    if not include_used:
        qs = qs.exclude(used_up=True)
    if color_filter and color_filter in INK_COLOR_HEX:
        qs = qs.filter(color=color_filter)
    for term in q.split():
        qs = qs.filter(
            Q(brand__name__icontains=term) | Q(name__icontains=term)
            | Q(line__icontains=term) | Q(color__icontains=term)
        )

    sort = request.GET.get("sort") or "color"
    if sort not in SORTS:
        sort = "color"
    inks = list(qs.annotate(n_usages=Count("usage")).order_by(*SORTS[sort][1]))
    for i in inks:
        i.hex = INK_COLOR_HEX.get(i.color, "#333")
        i.bg = i.swatch_bg

    if sort == "color":
        groups: dict[str, dict] = {}
        for color in INK_COLOR_HEX:
            groups[color] = {"color": color, "hex": INK_COLOR_HEX[color], "inks": []}
        for i in inks:
            if i.color in groups:
                groups[i.color]["inks"].append(i)
        ordered = [g for g in groups.values() if g["inks"]]
    else:
        ordered = [{"flat": True, "inks": inks}] if inks else []

    color_counts_qs = Ink.objects
    if not include_samples:
        color_counts_qs = color_counts_qs.filter(volume__gt=5)
    if not include_used:
        color_counts_qs = color_counts_qs.exclude(used_up=True)
    color_counts = dict(color_counts_qs.values_list("color").annotate(n=Count("pk")))
    color_chips = [
        {"color": c, "hex": INK_COLOR_HEX[c], "count": color_counts.get(c, 0)}
        for c in INK_COLOR_HEX
        if color_counts.get(c, 0) > 0
    ]

    # These URLs were each spelled out by hand, here and in the templates, and
    # every spelling listed the params it happened to remember — so the colour
    # chips dropped ?q= and the view toggle dropped anything typed since the
    # page rendered. Deriving them from the live query string means a control
    # can only ever set or clear its own key.
    def _url_with(**changes):
        params = request.GET.copy()
        for k, v in changes.items():
            if v:
                params[k] = v
            else:
                params.pop(k, None)
        qs_str = params.urlencode()
        return request.path + (("?" + qs_str) if qs_str else "")

    view = "grid" if request.GET.get("view") == "grid" else "list"

    for c in color_chips:
        c["url"] = _url_with(color=None if color_filter == c["color"] else c["color"])

    filters = {
        "include_samples": include_samples,
        "include_used": include_used,
        "color": color_filter,
        "q": q,
        "terms": q.split(),
        "color_chips": color_chips,
        "toggle_samples_url": _url_with(samples="1" if not include_samples else None),
        "toggle_used_url": _url_with(used="1" if not include_used else None),
        "clear_url": _url_with(samples=None, used=None, color=None, q=None),
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
        "inks": inks,
        "groups": ordered,
        "filters": filters,
        "public": public,
        "nav": "pub_inks" if public else "inks",
    }


def template_for(request, context):
    """List, grid or full page — the same choice on both routes."""
    partial = request.headers.get("HX-Request") and not request.headers.get("HX-Boosted")
    if not partial:
        return "items/inks/list.html"
    return "items/inks/_grid.html" if context["filters"]["view"] == "grid" else "items/inks/_content.html"
