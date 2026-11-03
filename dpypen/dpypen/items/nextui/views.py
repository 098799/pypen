"""The screens that exist only in the new version: the desk and the Stats."""

from __future__ import annotations

from datetime import date
from statistics import median

from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from dpypen.items import history, inkings, pairing
from dpypen.items.auth import login_or_guest_required
from dpypen.items.models import Pen, Usage
from dpypen.items.nextui import stats
from dpypen.items.public import UI_COOKIE


TABS = (
    ("nx_stats", "Overview"),
    ("nx_stats_inkings", "Inkings"),
    ("nx_stats_collection", "Collection"),
    ("nx_stats_cupboard", "Cupboard"),
    ("nx_stats_rotation", "Rotation"),
    ("nx_stats_timeline", "Timeline"),
    ("nx_stats_calendar", "Calendar"),
    ("nx_stats_pairs", "Pairings"),
    ("nx_records", "Records"),
)


def stat_tabs(active: str) -> list[dict]:
    return [{"url": reverse(name), "label": label, "on": name == active} for name, label in TABS]


def _desk_data(today):
    usages = list(Usage.objects.only("pen_id", "ink_id", "begin", "end"))
    past_by_pen: dict[int, list[int]] = {}
    all_fills = []
    for u in usages:
        if u.end:
            d = (u.end - u.begin).days
            past_by_pen.setdefault(u.pen_id, []).append(d)
            all_fills.append(d)
    usual_all = round(median(all_fills)) if all_fills else 0

    fills = []
    for u in (
        Usage.objects.filter(end__isnull=True)
        .select_related("pen__brand", "pen__rotation", "ink__brand", "nib")
        .prefetch_related("pen__photos")
        .order_by("-begin", "pk")
    ):
        days = (today - u.begin).days
        mine = past_by_pen.get(u.pen_id) or []
        usual = round(median(mine)) if len(mine) >= 2 else usual_all
        photos = list(u.pen.photos.all()[:1])
        fills.append({
            "u": u,
            "days": days,
            "usual": usual,
            "own": len(mine) >= 2,
            "pct": min(100, round(100 * days / (usual * 2))) if usual else 0,
            "mark": 50,
            "long": bool(usual and days > usual * 2),
            "photo": photos[0] if photos else None,
        })

    rots = pairing._pen_rotations()
    by_rot: dict[int, list] = {}
    for p in Pen.objects.filter(rotation__in=rots).select_related("brand").order_by("brand__name", "model"):
        by_rot.setdefault(p.rotation_id, []).append(p)
    due = pairing.due_pens(today, usages, rots, by_rot)

    up_next = None
    if due:
        pen = Pen.objects.select_related("brand", "rotation").prefetch_related("photos").get(pk=due[0]["pen_id"])
        d = due[0]
        photos = list(pen.photos.all()[:1])
        up_next = {
            "pen": pen,
            "photo": photos[0] if photos else None,
            "never": d["never"],
            "span": stats.span(d["rested"]) if d["rested"] is not None else None,
            "turn": stats.span(d["how_often"]),
            "picks": pairing.suggest_inks(pen, today, usages)[:3],
        }

    recent = list(
        Usage.objects.filter(end__isnull=False).select_related("pen__brand", "ink__brand").order_by("-end", "-pk")[:5]
    )
    for u in recent:
        u.days = (u.end - u.begin).days

    year = today.year
    this_year = [u for u in usages if u.begin.year == year]
    return {
        "fills": fills,
        "due_n": len(due),
        "up_next": up_next,
        "recent": recent,
        "year": year,
        "year_n": len(this_year),
        "year_pens": len({u.pen_id for u in this_year}),
        "year_inks": len({u.ink_id for u in this_year}),
        "no_photo": Pen.objects.filter(photos__isnull=True).count(),
    }


@login_or_guest_required
def desk(request):
    # The old page lived at this address: its bookmarks, ?pen= and ?shuffle=,
    # land on the same page here.
    if "pen" in request.GET or "shuffle" in request.GET:
        return HttpResponseRedirect(reverse("nx_pick") + "?" + request.META.get("QUERY_STRING", ""), status=307)
    return render(request, "next/desk.html", {**_desk_data(date.today()), "nav": "dashboard"})


@login_or_guest_required
def settings_page(request):
    return render(request, "next/settings.html", {"nav": "settings", "ui_first": request.COOKIES.get(UI_COOKIE) == "next"})


@login_or_guest_required
@require_POST
def prefer(request):
    """Which version opens first: a cookie, per device. Nothing in the collection
    moves, so a guest may choose too."""
    first = request.POST.get("first") == "next"
    leave = request.POST.get("leave") == "1"
    resp = redirect("/dashboard/" if leave else "nx_settings")
    if first:
        resp.set_cookie(UI_COOKIE, "next", max_age=400 * 86400, samesite="Lax", secure=request.is_secure(), httponly=True)
    else:
        resp.delete_cookie(UI_COOKIE)
    return resp


# ---- stats ---------------------------------------------------------------


def _stat(request, active, template, data, **more):
    return render(request, template, {**data, **more, "tabs": stat_tabs(active), "nav": "history"})


@login_or_guest_required
def stats_overview(request):
    return _stat(request, "nx_stats", "next/stats/overview.html", stats.cached("overview", stats.overview))


@login_or_guest_required
def stats_inkings(request):
    raw = request.GET.get("y", "")
    year = int(raw) if raw.isascii() and raw.isdigit() and len(raw) == 4 else None

    def build(y):
        return stats.cached(f"inkings:{y}", lambda: stats.rebase(inkings.build(y)))

    data = build(year)
    if year and year not in data.get("chart_years", []):
        year, data = None, build(None)
    return _stat(request, "nx_stats_inkings", "next/stats/inkings.html", data,
                 habits=stats.cached("habits", stats.habits) if not year else None)


@login_or_guest_required
def stats_collection(request):
    return _stat(request, "nx_stats_collection", "next/stats/collection.html", stats.cached("collection", stats.collection))


@login_or_guest_required
def stats_cupboard(request):
    return _stat(request, "nx_stats_cupboard", "next/stats/cupboard.html", stats.cached("cupboard", stats.cupboard))


@login_or_guest_required
def stats_rotation(request):
    return _stat(request, "nx_stats_rotation", "next/stats/rotation.html", stats.cached("rotation", stats.rotation))


def _in_group(pen, rot: str) -> bool:
    r = pen.rotation
    if not rot:
        return True
    if rot == "defunct":
        return not r.in_use
    mine = r.in_use and r.whos == "Tomek" and r.priority in (0, 1, 2, 3)
    if rot == "other":
        return r.in_use and not mine
    return bool(mine and rot == f"p{r.priority}")


@login_or_guest_required
def stats_timeline(request):
    data = stats.cached("gantt", history._gantt_data)
    rot = request.GET.get("rot", "")
    if rot not in {k for k, _ in history.GANTT_ROTS}:
        rot = ""
    rows = [r for r in data["pen_rows"] if _in_group(r["pen"], rot)]
    return _stat(request, "nx_stats_timeline", "next/stats/timeline.html", data, rows=rows, rot=rot, rot_chips=history.GANTT_ROTS)


@login_or_guest_required
def stats_calendar(request):
    raw = request.GET.get("y", "")
    year = int(raw) if raw.isascii() and raw.isdigit() else None
    return _stat(request, "nx_stats_calendar", "next/stats/calendar.html", stats.calendar_year(year))


@login_or_guest_required
def stats_pairs(request):
    return _stat(request, "nx_stats_pairs", "next/stats/pairs.html", stats.cached("pairs", stats.pairs))


def records(request):
    """The old view, with its tabs added: `skin.render` draws next/records.html."""
    from dpypen.items import records as old

    request.nx_tabs = stat_tabs("nx_records")
    return old.records(request)



