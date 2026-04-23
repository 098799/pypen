from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from dpypen.items.auth import login_or_guest_required
from dpypen.items.models import Brand, Ink, Pen, Rotation, Usage


INK_COLOR_HEX = {
    "Black": "#1f1d1a",
    "Blue": "#2a5caa",
    "Blue Black": "#1b2a4a",
    "Brown": "#6b4423",
    "Burgundy": "#6f1d2c",
    "Green": "#2e6b3a",
    "Grey": "#5b5b5b",
    "Orange": "#d46a2c",
    "Olive": "#6f6b2e",
    "Pink": "#d87aa5",
    "Purple": "#6b2e8c",
    "Red": "#b32c2c",
    "Royal Blue": "#2d4a8f",
    "Teal": "#2e6b73",
    "Turquoise": "#34a0a4",
    "Yellow": "#d4b12c",
}


WORD_NUMBERS = {
    0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
    6: "six", 7: "seven", 8: "eight", 9: "nine",
}


def spell(n: int) -> str:
    """Best-effort cardinal spelling for a couple of lovely hero numbers."""
    if n in WORD_NUMBERS:
        return WORD_NUMBERS[n]

    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
    teens = ["ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
             "sixteen", "seventeen", "eighteen", "nineteen"]

    def below_100(x: int) -> str:
        if x < 10:
            return WORD_NUMBERS[x]
        if x < 20:
            return teens[x - 10]
        t, r = divmod(x, 10)
        return tens[t] + ("-" + WORD_NUMBERS[r] if r else "")

    def below_1000(x: int) -> str:
        if x < 100:
            return below_100(x)
        h, r = divmod(x, 100)
        return WORD_NUMBERS[h] + " hundred" + (" " + below_100(r) if r else "")

    if n < 1000:
        return below_1000(n)
    thousands, rest = divmod(n, 1000)
    out = below_1000(thousands) + " thousand"
    if rest:
        out += (" " if rest >= 100 else " and ") + below_1000(rest)
    return out


def _days(begin, end, today):
    return ((end or today) - begin).days


def _pref_url(photo):
    """Prefer styled → thumbnail → original."""
    if not photo:
        return None
    if getattr(photo, "image_styled", None) and photo.image_styled:
        return photo.image_styled.url
    if getattr(photo, "thumbnail", None) and photo.thumbnail:
        return photo.thumbnail.url
    return photo.image.url if photo.image else None


def tease(request):
    today = date.today()
    current = []
    for u in (
        Usage.objects.filter(end__isnull=True)
        .select_related("pen__brand", "ink__brand", "nib")
        .prefetch_related("pen__photos")
        .order_by("-begin")
    ):
        photos = list(u.pen.photos.all()[:1])
        photo = photos[0] if photos else None
        current.append({
            "pen_id": u.pen.pk,
            "pen": str(u.pen),
            "pen_brand": u.pen.brand.name,
            "pen_model": u.pen.model + (f" {u.pen.finish}" if u.pen.finish else ""),
            "ink": str(u.ink),
            "ink_color": u.ink.color,
            "ink_hex": INK_COLOR_HEX.get(u.ink.color, "#333"),
            "ink_bg": u.ink.swatch_bg,
            "nib_html": str(u.nib),
            "days_inked": (today - u.begin).days,
            "photo_url": _pref_url(photo),
        })
    return render(request, "items/tease.html", {
        "current": current,
        "total_pens": Pen.objects.count(),
        "total_inks": Ink.objects.count(),
        "total_usages": Usage.objects.count(),
    })


@login_or_guest_required
def dashboard(request):
    today = date.today()
    year = today.year

    usages = list(
        Usage.objects.select_related("pen__brand", "ink__brand", "nib")
        .prefetch_related("pen__photos")
        .all()
    )

    current = []
    for u in sorted(
        (x for x in usages if x.end is None),
        key=lambda x: x.begin,
        reverse=True,
    ):
        photos = list(u.pen.photos.all()[:1])
        photo = photos[0] if photos else None
        current.append({
            "pen_id": u.pen.pk,
            "pen": str(u.pen),
            "pen_brand": u.pen.brand.name,
            "pen_model": u.pen.model + (f" {u.pen.finish}" if u.pen.finish else ""),
            "ink": str(u.ink),
            "ink_color": u.ink.color,
            "ink_hex": INK_COLOR_HEX.get(u.ink.color, "#333"),
            "ink_bg": u.ink.swatch_bg,
            "nib_html": str(u.nib),
            "days_inked": (today - u.begin).days,
            "begin": u.begin,
            "photo_url": _pref_url(photo),
        })

    total_pens = Pen.objects.count()
    total_inks = Ink.objects.count()
    total_usages = Usage.objects.count()
    total_brands = Brand.objects.count()

    first_usage = min((u.begin for u in usages), default=None)
    days_tracked = (today - first_usage).days if first_usage else 0
    total_days_inked = sum(_days(u.begin, u.end, today) for u in usages)

    rotations = []
    for r in Rotation.objects.filter(in_use=True, whos="Tomek", priority__in=[0, 1, 2, 3]).order_by("priority"):
        pens = list(
            Pen.objects.filter(rotation=r)
            .select_related("brand")
            .order_by("brand__name", "model")
        )
        rotations.append({
            "priority": r.priority,
            "how_often": r.how_often,
            "pens": pens,
            "count": len(pens),
        })

    ink_groups = []
    for color in INK_COLOR_HEX:
        inks = list(
            Ink.objects.filter(color=color, used_up=False, volume__gt=5)
            .select_related("brand")
            .order_by("brand__name", "name")
        )
        if inks:
            ink_groups.append({
                "color": color,
                "hex": INK_COLOR_HEX[color],
                "count": len(inks),
                "inks": inks,
            })

    recent_usages = sorted(usages, key=lambda u: u.begin, reverse=True)[:25]
    recent = []
    max_days = max((_days(u.begin, u.end, today) for u in recent_usages), default=1)
    for u in recent_usages:
        days = _days(u.begin, u.end, today)
        recent.append({
            "pen_short": f"{u.pen.brand.name} {u.pen.model}",
            "pen_id": u.pen_id,
            "ink": str(u.ink),
            "ink_id": u.ink_id,
            "ink_hex": INK_COLOR_HEX.get(u.ink.color, "#333"),
            "ink_bg": u.ink.swatch_bg,
            "begin": u.begin,
            "end": u.end,
            "days": days,
            "width_pct": max(2.5, 100 * days / max_days) if max_days else 2.5,
            "current": u.end is None,
        })

    pen_totals = {}
    pen_counts = {}
    for u in usages:
        pid = u.pen_id
        pen_totals[pid] = pen_totals.get(pid, 0) + _days(u.begin, u.end, today)
        pen_counts[pid] = pen_counts.get(pid, 0) + 1
    ink_totals = {}
    ink_counts = {}
    for u in usages:
        iid = u.ink_id
        ink_totals[iid] = ink_totals.get(iid, 0) + _days(u.begin, u.end, today)
        ink_counts[iid] = ink_counts.get(iid, 0) + 1

    workhorse = None
    if pen_totals:
        pid, total = max(pen_totals.items(), key=lambda kv: kv[1])
        pen = Pen.objects.select_related("brand").get(pk=pid)
        workhorse = {"pen": str(pen), "days": total, "inkings": pen_counts[pid]}

    beloved_ink = None
    if ink_totals:
        iid, total = max(ink_totals.items(), key=lambda kv: kv[1])
        ink = Ink.objects.select_related("brand").get(pk=iid)
        beloved_ink = {
            "ink": str(ink),
            "days": total,
            "inkings": ink_counts[iid],
            "hex": INK_COLOR_HEX.get(ink.color, "#333"),
            "bg": ink.swatch_bg,
        }

    most_inked_pen = None
    if pen_counts:
        pid, count = max(pen_counts.items(), key=lambda kv: kv[1])
        pen = Pen.objects.select_related("brand").get(pk=pid)
        most_inked_pen = {"pen": str(pen), "inkings": count}

    brand_counts = {}
    for p in Pen.objects.select_related("brand"):
        brand_counts[p.brand.name] = brand_counts.get(p.brand.name, 0) + 1
    top_brands = sorted(brand_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]

    year_usages = [u for u in usages if (u.end or today).year == year or u.begin.year == year]
    ytd_inkings = len(year_usages)
    ytd_pens = len({u.pen_id for u in year_usages})
    ytd_inks = len({u.ink_id for u in year_usages})
    ytd_days = sum(
        ((min(u.end or today, date(year, 12, 31)) - max(u.begin, date(year, 1, 1))).days + 1)
        for u in year_usages
        if (min(u.end or today, date(year, 12, 31)) >= max(u.begin, date(year, 1, 1)))
    )

    active_ink_count = Ink.objects.filter(used_up=False, volume__gt=5).count()

    return render(request, "items/home.html", {
        "current": current,
        "total_pens": total_pens,
        "total_inks": total_inks,
        "active_ink_count": active_ink_count,
        "total_usages": total_usages,
        "total_brands": total_brands,
        "total_days_inked": total_days_inked,
        "days_tracked": days_tracked,
        "year": year,
        "ytd_inkings": ytd_inkings,
        "ytd_pens": ytd_pens,
        "ytd_inks": ytd_inks,
        "ytd_days": ytd_days,
        "workhorse": workhorse,
        "beloved_ink": beloved_ink,
        "nav": "dashboard",
    })
