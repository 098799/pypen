import colorsys
from datetime import date

from django.shortcuts import get_object_or_404, render

from dpypen.items import inkindex
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
    """Full-bleed colour-spectrum wall of every ink in the collection.
    Standalone — no app shell. Includes samples and used-up bottles by default;
    each can be hidden via ?samples=0 / ?used_up=0."""
    hide_samples = request.GET.get("samples") == "0"
    hide_used = request.GET.get("used_up") == "0"
    qs = Ink.objects.select_related("brand")
    if hide_samples:
        qs = qs.filter(volume__gt=5)
    if hide_used:
        qs = qs.exclude(used_up=True)
    inks = list(qs)
    inks.sort(key=_spectrum_key)
    for i in inks:
        i.hex = INK_COLOR_HEX.get(i.color, "#333")
        i.bg = i.swatch_bg

    def _toggle(key, on):
        params = request.GET.copy()
        if on:
            params.pop(key, None)
        else:
            params[key] = "0"
        qs_ = params.urlencode()
        return request.path + (("?" + qs_) if qs_ else "")

    return render(request, "items/inks/wall.html", {
        "inks": inks,
        "total": len(inks),
        "brand_count": len({i.brand_id for i in inks}),
        "hide_samples": hide_samples,
        "hide_used": hide_used,
        "toggle_samples_url": _toggle("samples", hide_samples),
        "toggle_used_url": _toggle("used_up", hide_used),
    })


def pens_wall(request):
    """Full-bleed mosaic of every pen with a photo. Standalone — no app shell.
    Defunct pens hidden by default; ?defunct=1 to include them."""
    show_defunct = request.GET.get("defunct") == "1"
    qs = Pen.objects.select_related("brand", "rotation").prefetch_related("photos")
    if not show_defunct:
        qs = qs.filter(rotation__in_use=True)
    pens = list(qs.order_by(
        "-rotation__in_use", "rotation__priority", "brand__name", "model"
    ))

    photographed = []
    text_only = []
    for p in pens:
        photos = list(p.photos.all()[:1])
        ph = photos[0] if photos else None
        if ph:
            p.tile_url = ph.grid_url
            p.tile_styled = bool(ph.image_styled)
            photographed.append(p)
        else:
            p.tile_url = None
            p.tile_styled = False
            text_only.append(p)

    ordered = photographed + text_only

    def _toggle(key, on):
        params = request.GET.copy()
        if on:
            params.pop(key, None)
        else:
            params[key] = "1"
        qs_ = params.urlencode()
        return request.path + (("?" + qs_) if qs_ else "")

    return render(request, "items/pens/wall.html", {
        "pens": ordered,
        "total": len(ordered),
        "photo_count": len(photographed),
        "brand_count": len({p.brand_id for p in ordered}),
        "show_defunct": show_defunct,
        "toggle_defunct_url": _toggle("defunct", not show_defunct),
    })


def inks_gallery(request):
    """The ink cupboard, open to anyone. Same builder as the signed-in
    /inks/ — the two used to be forks and the public one's toolbar had rotted
    into dead links. See dpypen.items.inkindex."""
    context = inkindex.build(request, public=True)
    return render(request, inkindex.template_for(request, context), context)


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
                "ink_token": u.ink.share_token,
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
