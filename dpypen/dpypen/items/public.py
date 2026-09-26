from datetime import date
from collections import defaultdict


from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render

from dpypen.items.auth import login_or_guest_required
from dpypen.items.models import Brand, Ink, Pen, Rotation, Usage
from dpypen.items.pairing import due_pens


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


def _days(begin, end, today):
    return ((end or today) - begin).days


def _pref_url(photo):
    """Tile-sized: the styled thumb, then the plain one, then the originals."""
    return photo.grid_url if photo else None


def landing(request):
    """The door, and nothing else.

    This used to be the tease: the pens on the desk, each linking to its own
    public page, under a count of every pen, ink and inking in the collection.
    That was the whole of what a stranger could see, and it was too much of it.
    Now the front page says whose bureau this is and offers the one way in.
    It deliberately builds no context and touches no table — there is nothing
    here to leak, and it stays a 200 for the deploy script's smoke check even
    if the database is having a bad day.
    """
    return render(request, "items/landing.html")


def robots(request):
    """Nothing here is for crawlers while the door is shut."""
    body = "User-agent: *\nDisallow: /\n"
    if settings.PUBLIC_SHOWCASE:
        body = "User-agent: *\nAllow: /\n"
    return HttpResponse(body, content_type="text/plain")


@login_or_guest_required
def dashboard(request):
    today = date.today()
    year = today.year

    # Every inking feeds the totals, but only the dates and the two ids. The
    # page shows only the handful inked now, so only those rows get their pen,
    # ink, nib and brands joined in and their pens' photos fetched. Loading all
    # 564 inkings in full, with every pen's photos prefetched per row, was
    # ~3,900 model objects and ~190 ms of server time on bae for a page that
    # names a few of them. (It also built a 25-row "recent" list, rotation
    # cards and ink-by-colour groups that the template has long stopped
    # showing; they are gone.)
    usages = list(Usage.objects.only("pen_id", "ink_id", "begin", "end"))

    current = []
    # "pk" breaks ties the way the old stable in-Python sort did.
    for u in (
        Usage.objects.filter(end__isnull=True)
        .select_related("pen__brand", "ink__brand", "nib")
        .prefetch_related("pen__photos")
        .order_by("-begin", "pk")
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
    total_usages = len(usages)   # already materialised above
    total_brands = Brand.objects.count()

    first_usage = min((u.begin for u in usages), default=None)
    days_tracked = (today - first_usage).days if first_usage else 0
    total_days_inked = sum(_days(u.begin, u.end, today) for u in usages)

    # One query for every pen in the shown rotations, grouped in Python, rather
    # than one query per rotation.
    rots = list(
        Rotation.objects.filter(in_use=True, whos="Tomek", priority__in=[0, 1, 2, 3])
        .order_by("priority")
    )
    pens_by_rotation = defaultdict(list)
    for pen in (
        Pen.objects.filter(rotation__in=rots)
        .select_related("brand")
        .order_by("brand__name", "model")
    ):
        pens_by_rotation[pen.rotation_id].append(pen)

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

    # "What should I ink next": the pens past their turn. The ink half of the
    # question is answered on /next/ (dpypen.items.pairing).
    ready = due_pens(today, usages, rots, pens_by_rotation)
    next_up = ready[:6]

    pens_without_photos = Pen.objects.filter(photos__isnull=True).count()

    return render(request, "items/home.html", {
        "current": current,
        "next_up": next_up,
        "due_count": len(ready),
        "pens_without_photos": pens_without_photos,
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


@login_or_guest_required
def settings_page(request):
    """Theme, keyboard layer and the account actions.

    These lived in the hamburger panel, where they pushed the routes that have
    nowhere else to live — history, records, import — off the bottom of the
    screen. They are settings: visited rarely, changed rarely, and fine on a
    page of their own.
    """
    return render(request, "items/settings.html", {"nav": "settings"})
