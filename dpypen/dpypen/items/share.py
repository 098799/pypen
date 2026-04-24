import colorsys
from datetime import date

from django.db.models import Count
from django.shortcuts import get_object_or_404, render

from dpypen.items.models import Ink, Pen, Usage, WritingSample
from dpypen.items.public import INK_COLOR_HEX


def _hex_to_hls(hex_str: str) -> tuple[float, float, float]:
    h = (hex_str or "").lstrip("#")
    if len(h) != 6:
        return (0.0, 0.5, 0.0)
    try:
        r = int(h[0:2], 16) / 255
        g = int(h[2:4], 16) / 255
        b = int(h[4:6], 16) / 255
    except ValueError:
        return (0.0, 0.5, 0.0)
    return colorsys.rgb_to_hls(r, g, b)


def _spectrum_key(ink) -> tuple:
    """Sort key: chromatic colors by hue (warm → cool → back), greys/blacks at the end."""
    sample = ink.sampled_hex[0] if ink.sampled_hex else INK_COLOR_HEX.get(ink.color, "#333")
    h, l, s = _hex_to_hls(sample)
    if s < 0.18:
        # Achromatic: cluster together at the end, ordered light → dark
        return (1, -l)
    return (0, h, -l)


def inks_wall(request):
    """Full-bleed colour-spectrum wall of every bottle. Standalone — no app shell."""
    inks = list(
        Ink.objects.select_related("brand")
        .filter(volume__gt=5)
        .exclude(used_up=True)
    )
    inks.sort(key=_spectrum_key)
    for i in inks:
        i.hex = INK_COLOR_HEX.get(i.color, "#333")
        i.bg = i.swatch_bg

    return render(request, "items/inks/wall.html", {
        "inks": inks,
        "total": len(inks),
        "brand_count": len({i.brand_id for i in inks}),
    })


def inks_gallery(request):
    include_samples = request.GET.get("samples") == "1"
    include_used = request.GET.get("used") == "1"
    color_filter = request.GET.get("color", "")

    qs = Ink.objects.select_related("brand", "rotation")
    if not include_samples:
        qs = qs.filter(volume__gt=5)
    if not include_used:
        qs = qs.exclude(used_up=True)
    if color_filter and color_filter in INK_COLOR_HEX:
        qs = qs.filter(color=color_filter)

    inks = list(qs.order_by("used_up", "brand__name", "name"))
    for i in inks:
        i.hex = INK_COLOR_HEX.get(i.color, "#333")
        i.bg = i.swatch_bg

    groups: dict[str, dict] = {}
    for color in INK_COLOR_HEX:
        groups[color] = {"color": color, "hex": INK_COLOR_HEX[color], "inks": []}
    for i in inks:
        if i.color in groups:
            groups[i.color]["inks"].append(i)
    ordered = [g for g in groups.values() if g["inks"]]

    color_counts_qs = Ink.objects
    if not include_samples:
        color_counts_qs = color_counts_qs.filter(volume__gt=5)
    if not include_used:
        color_counts_qs = color_counts_qs.exclude(used_up=True)
    color_counts = dict(color_counts_qs.values_list("color").annotate(n=Count("pk")))
    color_chips = [
        {"color": c, "hex": INK_COLOR_HEX[c], "count": color_counts.get(c, 0)}
        for c in INK_COLOR_HEX if color_counts.get(c, 0) > 0
    ]

    def _toggle_url(key, new_val):
        params = request.GET.copy()
        if new_val: params[key] = new_val
        else: params.pop(key, None)
        q = params.urlencode()
        return request.path + (("?" + q) if q else "")

    filters = {
        "include_samples": include_samples,
        "include_used": include_used,
        "color": color_filter,
        "color_chips": color_chips,
        "q": "",
        "terms": [],
        "toggle_samples_url": _toggle_url("samples", "1" if not include_samples else ""),
        "toggle_used_url": _toggle_url("used", "1" if not include_used else ""),
    }

    context = {
        "inks": inks,
        "groups": ordered,
        "filters": filters,
        "public": True,
        "can_edit": False,
        "nav": None,
    }
    partial = request.headers.get("HX-Request") and not request.headers.get("HX-Boosted")
    template = "items/inks/_content.html" if partial else "items/inks/list.html"
    return render(request, template, context)


def pen_by_token(request, token):
    pen = get_object_or_404(Pen.objects.select_related("brand", "rotation"), share_token=token)
    photos = list(pen.photos.all())
    usages = list(
        Usage.objects.filter(pen=pen)
        .select_related("ink__brand", "nib")
        .order_by("-begin")
    )
    today = date.today()
    for u in usages:
        u.days = ((u.end or today) - u.begin).days
        u.ink_hex = INK_COLOR_HEX.get(u.ink.color, "#333")
        u.ink_bg = u.ink.swatch_bg
    current = next((u for u in usages if u.end is None), None)
    past = [u for u in usages if u.end is not None]
    total_days = sum(u.days for u in usages)
    distinct_inks = len({u.ink_id for u in usages})

    gantt_bars, year_ticks = [], []
    if usages:
        earliest = min(u.begin for u in usages)
        start_date = date(earliest.year, 1, 1)
        end_date = date(today.year, 12, 31)
        total_span = max((end_date - start_date).days, 1)
        for u in sorted(usages, key=lambda x: x.begin):
            b = max(u.begin, start_date)
            e = min(u.end or today, end_date)
            if e < b:
                continue
            gantt_bars.append({
                "left": (b - start_date).days / total_span * 100,
                "width": max(0.25, (e - b).days / total_span * 100),
                "hex": u.ink_hex,
                "ink": str(u.ink),
                "ink_id": u.ink_id,
                "nib": str(u.nib),
                "begin": u.begin,
                "end": u.end,
                "days": u.days,
                "current": u.end is None,
            })
        year_ticks = [
            {"year": y, "left": (date(y, 1, 1) - start_date).days / total_span * 100}
            for y in range(earliest.year, today.year + 1)
        ]

    samples = list(
        WritingSample.objects.filter(usage__pen=pen)
        .select_related("usage__ink__brand")
        .order_by("-uploaded_at")[:18]
    )

    return render(request, "items/pens/detail.html", {
        "pen": pen,
        "photos": photos,
        "current": current,
        "past": past,
        "total_days": total_days,
        "total_usages": len(usages),
        "distinct_inks": distinct_inks,
        "gantt_bars": gantt_bars,
        "year_ticks": year_ticks,
        "samples": samples,
        "public": True,
        "nav": None,
    })


def ink_by_token(request, token):
    ink = get_object_or_404(Ink.objects.select_related("brand", "rotation"), share_token=token)
    today = date.today()
    usages = list(
        Usage.objects.filter(ink=ink)
        .select_related("pen__brand", "nib")
        .order_by("-begin")
    )
    for u in usages:
        u.days = ((u.end or today) - u.begin).days
    current = [u for u in usages if u.end is None]
    past = [u for u in usages if u.end is not None]
    total_days = sum(u.days for u in usages)
    distinct_pens = len({u.pen_id for u in usages})
    samples = list(
        WritingSample.objects.filter(usage__ink=ink)
        .select_related("usage__pen__brand")
        .order_by("-uploaded_at")[:18]
    )
    return render(request, "items/inks/detail.html", {
        "ink": ink,
        "ink_hex": INK_COLOR_HEX.get(ink.color, "#333"),
        "ink_bg": ink.swatch_bg,
        "current": current,
        "past": past,
        "total_days": total_days,
        "total_usages": len(usages),
        "distinct_pens": distinct_pens,
        "samples": samples,
        "public": True,
        "nav": None,
    })
