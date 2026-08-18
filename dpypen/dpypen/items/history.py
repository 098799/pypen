from collections import defaultdict
from datetime import date, timedelta

from django.core.cache import cache
from django.shortcuts import render

from dpypen.items.auth import login_or_guest_required
from dpypen.items.models import Ink, Pen, Usage
from dpypen.items.public import INK_COLOR_HEX


YEAR_WINDOW = 15
TO_PLN = {
    "PLN": 1.0, "EUR": 4.3, "USD": 4.0, "GBP": 5.0, "CHF": 4.6,
    "JPY": 0.027, "CAD": 2.9, "AUD": 2.6, "SEK": 0.38, "CZK": 0.17,
}


def _pln(money):
    if not money or not getattr(money, "amount", None):
        return 0
    code = str(money.currency.code) if hasattr(money.currency, "code") else str(money.currency)
    return float(money.amount) * TO_PLN.get(code, 0)


def _bounds():
    today = date.today()
    earliest_year = Usage.objects.order_by("begin").values_list("begin", flat=True).first()
    earliest_year = earliest_year.year if earliest_year else today.year
    latest_year = today.year
    start_year = max(earliest_year, latest_year - YEAR_WINDOW + 1)
    return today, start_year, latest_year


def _sub_nav(active):
    return [
        {"key": "overview", "label": "Overview", "url": "/history/", "active": active == "overview"},
        {"key": "calendar", "label": "Calendar", "url": "/history/calendar/", "active": active == "calendar"},
        {"key": "gantt", "label": "Per-pen Gantt", "url": "/history/gantt/", "active": active == "gantt"},
        {"key": "matrix", "label": "Pen × Ink", "url": "/history/matrix/", "active": active == "matrix"},
    ]


def _overview_data():
    today, start_year, latest_year = _bounds()
    usages = list(Usage.objects.only("begin", "end", "pen_id", "ink_id"))
    year_stats = {}
    for y in range(start_year, latest_year + 1):
        year_stats[y] = {"year": y, "inkings": 0, "pens": set(), "inks": set(), "days": 0}
    for u in usages:
        u_start = u.begin
        u_end = u.end or today
        for y in range(max(u_start.year, start_year), min(u_end.year, latest_year) + 1):
            s = year_stats[y]
            s["inkings"] += 1
            s["pens"].add(u.pen_id)
            s["inks"].add(u.ink_id)
            year_begin = date(y, 1, 1)
            year_finish = date(y, 12, 31)
            b_d = max(u_start, year_begin)
            e_d = min(u_end, year_finish)
            if e_d >= b_d:
                s["days"] += (e_d - b_d).days + 1
    max_days = max((s["days"] for s in year_stats.values()), default=1) or 1
    year_list = []
    for y in sorted(year_stats):
        s = year_stats[y]
        year_list.append({
            "year": y, "inkings": s["inkings"],
            "pens": len(s["pens"]), "inks": len(s["inks"]),
            "days": s["days"],
            "bar_pct": max(0.5, 100 * s["days"] / max_days),
        })

    yearly = {}
    earliest_acq = latest_year
    for p in Pen.objects.only("obtained", "price_currency", "price"):
        if not p.obtained: continue
        y = p.obtained.year
        earliest_acq = min(earliest_acq, y)
        yearly.setdefault(y, {"pen_count": 0, "ink_count": 0, "pen_spend": 0.0, "ink_spend": 0.0})
        yearly[y]["pen_count"] += 1
        yearly[y]["pen_spend"] += _pln(p.price)
    for i in Ink.objects.only("obtained", "price_currency", "price"):
        if not i.obtained: continue
        y = i.obtained.year
        earliest_acq = min(earliest_acq, y)
        yearly.setdefault(y, {"pen_count": 0, "ink_count": 0, "pen_spend": 0.0, "ink_spend": 0.0})
        yearly[y]["ink_count"] += 1
        yearly[y]["ink_spend"] += _pln(i.price)
    all_years = list(range(earliest_acq, latest_year + 1))
    for y in all_years:
        yearly.setdefault(y, {"pen_count": 0, "ink_count": 0, "pen_spend": 0.0, "ink_spend": 0.0})
    def _chart(metric):
        rows = [(y, yearly[y][metric]) for y in all_years]
        peak = max((v for _, v in rows), default=1) or 1
        return [{"year": y, "value": v, "pct": max(0.5, 100 * v / peak) if v else 0} for y, v in rows]

    return {
        "year_list": year_list,
        "yearly_pen_count": _chart("pen_count"),
        "yearly_ink_count": _chart("ink_count"),
        "yearly_pen_spend": _chart("pen_spend"),
        "yearly_ink_spend": _chart("ink_spend"),
        "start_year": start_year,
        "latest_year": latest_year,
    }


def _calendar_data():
    today, start_year, latest_year = _bounds()
    usages = list(Usage.objects.select_related("ink", "pen__brand").only(
        "begin", "end", "ink__color", "ink__brand__name", "ink__name", "ink__line", "ink__volume",
        "pen__model", "pen__brand__name", "pen__finish"
    ))
    day_ink: dict[date, list[dict]] = defaultdict(list)
    for u in usages:
        b = u.begin
        e = u.end or today
        payload = {
            "hex": INK_COLOR_HEX.get(u.ink.color, "#333"),
            "ink": str(u.ink),
            "pen": str(u.pen),
        }
        cur = b
        while cur <= e:
            day_ink[cur].append(payload)
            cur += timedelta(days=1)

    calendar_years = []
    for y in range(start_year, latest_year + 1):
        year_start = date(y, 1, 1)
        year_end = date(y, 12, 31) if y < today.year else today
        weeks = [[None] * 7 for _ in range(54)]
        d = year_start
        first_dow = year_start.weekday()
        week_idx = 0
        day_idx = first_dow
        active_days = 0
        while d <= year_end:
            inks = day_ink.get(d) or []
            if not inks:
                bg = None
            elif len(inks) == 1:
                bg = inks[0]["hex"]
            else:
                step = 100 / len(inks)
                stops = []
                for i, p in enumerate(inks):
                    start = round(i * step, 2); end = round((i + 1) * step, 2)
                    stops.append(f"{p['hex']} {start}% {end}%")
                bg = "linear-gradient(to bottom," + ",".join(stops) + ")"
            if inks: active_days += 1
            weeks[week_idx][day_idx] = {
                "date": d, "bg": bg,
                "inks_summary": " · ".join(p["ink"] for p in inks),
                "pens_summary": " · ".join(p["pen"] for p in inks),
                "count": len(inks),
                "label": d.strftime("%b %-d, %Y"),
            }
            day_idx += 1
            if day_idx > 6:
                day_idx = 0; week_idx += 1
            d += timedelta(days=1)
        max_w = 0
        for w_i, week in enumerate(weeks):
            if any(c for c in week): max_w = w_i + 1
        calendar_years.append({"year": y, "weeks": weeks[:max_w], "active_days": active_days})
    return {"calendar_years": calendar_years, "start_year": start_year, "latest_year": latest_year}


def _gantt_data():
    today, start_year, latest_year = _bounds()
    pens = list(Pen.objects.select_related("brand", "rotation")
                .order_by("-rotation__in_use", "rotation__priority", "brand__name", "model"))
    usages = list(Usage.objects.select_related("pen", "ink__brand", "nib"))
    by_pen: dict[int, list[Usage]] = defaultdict(list)
    for u in usages: by_pen[u.pen_id].append(u)

    start_date = date(start_year, 1, 1)
    end_date = date(latest_year, 12, 31)
    total_days = max((end_date - start_date).days, 1)

    pen_rows = []
    for p in pens:
        bars = []
        for u in by_pen.get(p.pk, []):
            b_date = max(u.begin, start_date)
            e_date = min(u.end or today, end_date)
            if e_date < b_date: continue
            bars.append({
                "left": (b_date - start_date).days / total_days * 100,
                "width": max(0.2, (e_date - b_date).days / total_days * 100),
                "hex": INK_COLOR_HEX.get(u.ink.color, "#333"),
                "bg": u.ink.swatch_bg,
                "ink": str(u.ink), "ink_id": u.ink_id,
                "pen": str(u.pen), "pen_id": u.pen_id,
                "nib": str(u.nib), "begin": u.begin, "end": u.end,
                "days": ((u.end or today) - u.begin).days,
                "current": u.end is None,
            })
        if bars:
            pen_rows.append({"pen": p, "bars": bars})

    year_ticks = [
        {"year": y, "left": (date(y, 1, 1) - start_date).days / total_days * 100}
        for y in range(start_year, latest_year + 1)
    ]
    return {
        "pen_rows": pen_rows,
        "year_ticks": year_ticks,
        "start_year": start_year,
        "latest_year": latest_year,
        "total_pens": len(pen_rows),
    }


def _matrix_data():
    today = date.today()
    usages = list(Usage.objects.only("begin", "end", "pen_id", "ink_id"))
    pair_days: dict[tuple[int, int], int] = {}
    pair_fills = {}
    pen_total_days: dict[int, int] = {}
    ink_total_days: dict[int, int] = {}
    for u in usages:
        d = ((u.end or today) - u.begin).days or 1
        key = (u.pen_id, u.ink_id)
        pair_days[key] = pair_days.get(key, 0) + d
        pair_fills[key] = pair_fills.get(key, 0) + 1
        pen_total_days[u.pen_id] = pen_total_days.get(u.pen_id, 0) + d
        ink_total_days[u.ink_id] = ink_total_days.get(u.ink_id, 0) + d

    N = 24
    top_pen_ids = [pid for pid, _ in sorted(pen_total_days.items(), key=lambda kv: -kv[1])[:N]]
    top_ink_ids = [iid for iid, _ in sorted(ink_total_days.items(), key=lambda kv: -kv[1])[:N]]
    pen_lookup = {p.pk: p for p in Pen.objects.filter(pk__in=top_pen_ids).select_related("brand")}
    ink_lookup = {i.pk: i for i in Ink.objects.filter(pk__in=top_ink_ids).select_related("brand")}

    max_cell = max((pair_days[(p, i)] for p in top_pen_ids for i in top_ink_ids if (p, i) in pair_days), default=1) or 1
    matrix_rows = []
    for pid in top_pen_ids:
        pen = pen_lookup.get(pid)
        if not pen: continue
        row_cells = []
        for iid in top_ink_ids:
            ink = ink_lookup.get(iid)
            if not ink: row_cells.append(None); continue
            d = pair_days.get((pid, iid), 0)
            f = pair_fills.get((pid, iid), 0)
            opacity = min(1.0, d / max_cell) if d else 0
            row_cells.append({
                "days": d, "fills": f,
                "hex": INK_COLOR_HEX.get(ink.color, "#333"),
                "opacity": round(opacity, 3),
                "ink_id": iid, "ink_label": str(ink),
            })
        matrix_rows.append({"pen": pen, "pen_id": pid, "cells": row_cells})
    matrix_cols = []
    for iid in top_ink_ids:
        ink = ink_lookup.get(iid)
        if not ink: continue
        matrix_cols.append({"ink": ink, "ink_id": iid,
                            "hex": INK_COLOR_HEX.get(ink.color, "#333"),
                            "bg": ink.swatch_bg,
                            "label": str(ink)})
    return {"matrix_rows": matrix_rows, "matrix_cols": matrix_cols}


def _cached(kind, fn):
    key = f"history:{kind}"
    data = cache.get(key)
    if data is not None:
        return data
    data = fn()
    cache.set(key, data, 240)
    return data


@login_or_guest_required
def overview(request):
    data = _cached("overview", _overview_data)
    return render(request, "items/history.html", {
        **data, "section": "overview", "sub_nav": _sub_nav("overview"), "nav": "history",
    })


@login_or_guest_required
def calendar(request):
    data = _cached("calendar", _calendar_data)
    return render(request, "items/history.html", {
        **data, "section": "calendar", "sub_nav": _sub_nav("calendar"), "nav": "history",
    })


@login_or_guest_required
def gantt(request):
    data = _cached("gantt", _gantt_data)
    return render(request, "items/history.html", {
        **data, "section": "gantt", "sub_nav": _sub_nav("gantt"), "nav": "history",
    })


@login_or_guest_required
def matrix(request):
    data = _cached("matrix", _matrix_data)
    return render(request, "items/history.html", {
        **data, "section": "matrix", "sub_nav": _sub_nav("matrix"), "nav": "history",
    })


# Backwards compat alias
history = overview
