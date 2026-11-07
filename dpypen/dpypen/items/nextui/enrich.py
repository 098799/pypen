"""What the new version's pages show beyond what the shared view hands them.

`skin.render` calls `apply` on the way to a template under next/. The old pages
do not pay for any of this, and the new ones add queries only per page, never
per row: a list's rows get their history from one IN query.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from statistics import median



from dpypen.items import pairing, shelf
from dpypen.items.models import Ink, Pen, Usage
from dpypen.items.nextui import color, stats
from dpypen.items.public import INK_COLOR_HEX

TRAIL = 7


def _pens(request, ctx):
    rows = ctx.get("pens") or []
    if not rows:
        return ctx
    today = date.today()
    by_pen = defaultdict(list)
    for u in Usage.objects.filter(pen__in=[p.pk for p in rows]).select_related("ink").order_by("begin", "pk"):
        by_pen[u.pen_id].append(u)
    for p in rows:
        mine = by_pen[p.pk]
        p.fills = len(mine)
        p.trail = [{"bg": u.ink.swatch_bg, "name": u.ink.name} for u in mine[-TRAIL:]]
        p.now = next((u for u in reversed(mine) if u.end is None), None)
        ends = [u.end for u in mine if u.end]
        p.rested = stats.span((today - max(ends)).days) if ends and not p.now else None
    return ctx


def _inks(request, ctx):
    rows = ctx.get("inks") or []
    if not rows:
        return ctx
    fills = Counter()
    now = defaultdict(list)
    last = {}
    for u in Usage.objects.filter(ink__in=[i.pk for i in rows]).select_related("pen__brand"):
        fills[u.ink_id] += 1
        if u.end is None:
            now[u.ink_id].append(u.pen)
        elif u.ink_id not in last or u.end > last[u.ink_id]:
            last[u.ink_id] = u.end
    for i in rows:
        i.fills = fills[i.pk]
        i.in_pens = now[i.pk]
        i.last_end = shelf.ago(last.get(i.pk)) if i.pk in last else ""
    return ctx


def _pen_detail(request, ctx):
    pen = ctx["pen"]
    today = date.today()
    current, past = ctx.get("current"), ctx.get("past") or []
    ended = [u.days for u in past]
    price = stats.pln(pen.price)
    days = ctx.get("total_days", 0)
    nibs = Counter(str(u.nib) for u in past)
    inks = Counter(u.ink.pk for u in past)
    if current:
        nibs[str(current.nib)] += 1
        inks[current.ink.pk] += 1
    fav_ink = None
    if inks:
        pk, n = inks.most_common(1)[0]
        if n > 1:
            u = next(u for u in ([current] if current else []) + past if u.ink.pk == pk)
            fav_ink = {"ink": u.ink, "n": n}
    rested = None
    if not current and past:
        rested = (today - max(u.end for u in past)).days
    turn = pen.rotation.how_often if pen.rotation.in_use and pen.rotation.how_often > 0 else None

    usages = list(Usage.objects.only("pen_id", "ink_id", "begin", "end"))
    picks = pairing.suggest_inks(pen, today, usages)[:3]
    return {
        **ctx,
        "year_bars": stats.rebase(ctx.get("year_bars")),
        "x": {
            "median_fill": round(median(ended)) if ended else None,
            "price_pln": round(price) if price else None,
            "per_day": (f"{price / days:.2f}" if price / days < 10 else f"{price / days:.0f}") if price and days else None,
            "fav_nib": nibs.most_common(1)[0][0] if nibs else None,
            "fav_nib_n": nibs.most_common(1)[0][1] if nibs else 0,
            "fav_ink": fav_ink,
            "rested": stats.span(rested) if rested is not None else None,
            "turn": stats.span(turn) if turn else None,
            "late": rested is not None and turn is not None and rested > turn,
        },
        "picks": picks,
    }


def _close_inks(ink, n=5):
    mine = color.ink_hex(ink, INK_COLOR_HEX)
    others = []
    for other in Ink.objects.select_related("brand").exclude(pk=ink.pk).filter(volume__gt=5).exclude(used_up=True):
        others.append((color.distance(mine, color.ink_hex(other, INK_COLOR_HEX)), other))
    others.sort(key=lambda t: t[0])
    return [o for _, o in others[:n]]


def _ink_detail(request, ctx):
    ink = ctx["ink"]
    today = date.today()
    usages = list(ctx.get("current") or []) + list(ctx.get("past") or [])
    pens = Counter()
    pen_of = {}
    for u in usages:
        pens[u.pen_id] += 1
        pen_of[u.pen_id] = u.pen
    worn = [{"pen": pen_of[pk], "n": n} for pk, n in pens.most_common(6)]
    price = stats.pln(ink.price)

    # Pens past their turn that have never held it: where this bottle could go.
    all_usages = list(Usage.objects.only("pen_id", "ink_id", "begin", "end"))
    rots = pairing._pen_rotations()
    by_rot = defaultdict(list)
    for p in Pen.objects.filter(rotation__in=rots).select_related("brand").order_by("brand__name", "model"):
        by_rot[p.rotation_id].append(p)
    due = pairing.due_pens(today, all_usages, rots, by_rot)
    had = {u.pen_id for u in all_usages if u.ink_id == ink.pk}
    open_to = [d for d in due if d["pen_id"] not in had][:4]
    ended = [u.days for u in ctx.get("past") or []]
    last = max((u.end for u in ctx.get("past") or []), default=None)
    return {
        **ctx,
        "year_bars": stats.rebase(ctx.get("year_bars")),
        "x": {
            "per_ml": f"{price / ink.volume:.2f}" if price and ink.volume else None,
            "price_pln": round(price) if price else None,
            "median_fill": round(median(ended)) if ended else None,
            "rested": stats.span((today - last).days) if last and not ctx.get("current") else None,
            "hex": list(ink.sampled_hex or []),
            "hue": color.ink_hex(ink, INK_COLOR_HEX),
        },
        "worn": worn,
        "close": _close_inks(ink),
        "open_to": open_to,
    }


def _search(request, ctx):
    _pens(request, ctx)
    return ctx


def _pick(request, ctx):
    pen = ctx.get("pen")
    if pen is not None:
        for d in ctx.get("due", []):
            if d["pen_id"] == pen.pk:
                ctx["this_due"] = d
                d["span"] = stats.span(d["rested"]) if d["rested"] is not None else None
                d["turn"] = stats.span(d["how_often"])
                break
        ctx["photo"] = pen.photos.first()
    for s in ctx.get("suggestions", []):
        s.warn = [t for tone, t in s.reasons if tone == "warn"]
        s.good = [t for tone, t in s.reasons if tone == "good"]
        s.plain = [t for tone, t in s.reasons if tone not in ("warn", "good")]
    return ctx


_BY_TEMPLATE = {
    "next/pens/list.html": _pens,
    "next/pens/_list_content.html": _pens,
    "next/pens/_grid_content.html": _pens,
    "next/inks/list.html": _inks,
    "next/inks/_content.html": _inks,
    "next/inks/_grid.html": _inks,
    "next/pens/detail.html": _pen_detail,
    "next/inks/detail.html": _ink_detail,
    "next/search.html": _search,
    "next/_search_results.html": _search,
    "next/next.html": _pick,
}


def apply(template: str, request, ctx: dict) -> dict:
    fn = _BY_TEMPLATE.get(template)
    return fn(request, ctx) if fn else ctx



