"""The charts of the ink-ups (PYPEN-10): what `/history/inkings/` draws, and the
small per-year bars on a pen's and an ink's page.

An ink-up counts on the day it began: `Usage.begin`. A fill that runs over New
Year counts once, in the year it was poured. "On the desk" is the other reading
and has its own chart: how many pens held ink on a day.

Everything here is plain numbers for the templates, computed from
`Usage` rows in Python: the collection is a few hundred rows and the view caches.

Colour: the 16 ink colours are data, so a ranked list shows them as they are,
with their names beside them. Sixteen of them in a stack that is 20 px wide is
mud, so the stacks fold them into eight families (`FAMILIES`), which app.css
("Charts") draws with `.fam-*`, a step for each theme.
"""

from __future__ import annotations

import calendar
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import median
from urllib.parse import urlencode

from django.urls import reverse

from dpypen.items.models import Ink, Pen, Usage
from dpypen.items.public import INK_COLOR_HEX

# (slug, name, the ink colours in it), bottom of a stack first. Blacks at the
# foot, then the spectrum, so a stack reads alike from column to column.
FAMILIES = (
    ("black", "Black & grey", ("Black", "Grey")),
    ("blue", "Blue", ("Blue Black", "Royal Blue", "Blue")),
    ("teal", "Teal", ("Turquoise", "Teal")),
    ("green", "Green", ("Green", "Olive")),
    ("amber", "Yellow & orange", ("Yellow", "Orange")),
    ("red", "Red", ("Red", "Burgundy")),
    ("violet", "Pink & purple", ("Pink", "Purple")),
    ("brown", "Brown", ("Brown",)),
)
_FAMILY_OF = {c: slug for slug, _, colors in FAMILIES for c in colors}
_FAMILY_ORDER = {slug: i for i, (slug, _, _) in enumerate(FAMILIES)}
_FAMILY_NAME = {slug: name for slug, name, _ in FAMILIES}
OTHER = "other"  # a colour named after this list was written: still counted, still drawn

COLOR_ORDER = tuple(c for _, _, colors in FAMILIES for c in colors)

MONTHS = tuple(calendar.month_abbr[m] for m in range(1, 13))
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
# (top in days, exclusive; label). A long fill is rare and a short one is the
# point, so the bands grow.
DURATIONS = (
    (7, "< 1 wk"), (14, "1–2 wk"), (30, "2–4 wk"), (60, "1–2 mo"),
    (90, "2–3 mo"), (180, "3–6 mo"), (None, "6 mo +"),
)
TOP_N = 8


@dataclass(frozen=True, slots=True)
class Row:
    begin: date
    end: date | None
    pen_id: int
    ink_id: int
    color: str


def load_rows() -> list[Row]:
    return [Row(*v) for v in Usage.objects.values_list("begin", "end", "pen_id", "ink_id", "ink__color")]


def plural(n: int, word: str = "inking") -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def usages_url(began: str = "", color: str = "") -> str:
    """The list of the ink-ups a mark on a chart counts."""
    q = {k: v for k, v in (("began", began), ("color", color)) if v}
    return reverse("usages_list") + ("?" + urlencode(q) if q else "")


def _segments(colors: Counter) -> list[dict]:
    """A column's stack, bottom first. `share` is % of the column."""
    fams: Counter = Counter()
    for color, n in colors.items():
        fams[_FAMILY_OF.get(color, OTHER)] += n
    total = sum(fams.values()) or 1
    order = sorted(fams, key=lambda f: _FAMILY_ORDER.get(f, 99))
    return [{"fam": f, "name": _FAMILY_NAME.get(f, "Other"), "n": fams[f], "share": round(100 * fams[f] / total, 2)} for f in order]


def _column(key, label: str, colors: Counter, peak: int, title: str, links: str = "") -> dict:
    total = sum(colors.values())
    segs = _segments(colors)
    return {
        "key": key,
        "label": label,
        "n": total,
        "pct": round(100 * total / peak, 2) if peak else 0,
        "segs": segs,
        "title": title,
        "tip": "\n".join(f"{s['n']} {s['name']}" for s in reversed(segs)) if total else "no inkings",
        "links": links,
    }


def _legend(rows: list[Row]) -> list[dict]:
    """The families in these rows, in stack order; the chart's key."""
    fams = Counter(_FAMILY_OF.get(r.color, OTHER) for r in rows)
    return [{"fam": f, "name": _FAMILY_NAME.get(f, "Other"), "n": fams[f]}
            for f in sorted(fams, key=lambda x: _FAMILY_ORDER.get(x, 99))]


def _years_columns(rows: list[Row], first: int, last: int) -> list[dict]:
    per: dict[int, Counter] = defaultdict(Counter)
    for r in rows:
        per[r.begin.year][r.color] += 1
    peak = max((sum(c.values()) for c in per.values()), default=0)
    cols = []
    for y in range(first, last + 1):
        links = f"The year's charts|{reverse('history_inkings')}?y={y}\nSee them|{usages_url(str(y))}" if per[y] else ""
        cols.append(_column(y, f"’{y % 100:02d}", per[y], peak, str(y), links))
    return cols


def _months_columns(rows: list[Row], year: int, today: date) -> list[dict]:
    per: dict[int, Counter] = defaultdict(Counter)
    for r in rows:
        per[r.begin.month][r.color] += 1
    peak = max((sum(c.values()) for c in per.values()), default=0)
    cols = []
    for m in range(1, 13):
        links = f"See them|{usages_url(f'{year}-{m:02d}')}" if per[m] else ""
        col = _column(m, MONTHS[m - 1][0], per[m], peak, f"{MONTHS[m - 1]} {year}", links)
        col["ahead"] = date(year, m, 1) > today  # a month that has not come yet is no quiet month
        cols.append(col)
    return cols


def _heatmap(rows: list[Row], first: int, last: int, today: date) -> dict:
    counts = Counter((r.begin.year, r.begin.month) for r in rows)
    peak = max(counts.values(), default=1)
    table = []
    for y in range(last, first - 1, -1):
        cells = []
        for m in range(1, 13):
            n = counts[(y, m)]
            cells.append({
                "n": n,
                "a": round(0.18 + 0.82 * n / peak, 3) if n else 0,
                "title": f"{MONTHS[m - 1]} {y}",
                "tip": plural(n),
                "links": f"See them|{usages_url(f'{y}-{m:02d}')}" if n else "",
                "ahead": date(y, m, 1) > today,
            })
        table.append({"year": y, "cells": cells, "total": sum(c["n"] for c in cells)})
    return {"rows": table, "heads": [m[0] for m in MONTHS], "peak": peak}


def _desk_line(rows: list[Row], start: date, stop: date) -> dict:
    """Pens holding ink on each day from `start` to `stop`, sampled: a value a
    week over years (the highest of its week, so a busy day shows), a value a
    day over one year."""
    delta: Counter = Counter()
    for r in rows:
        begin, end = max(r.begin, start), min(r.end or stop, stop)
        if end < begin:
            continue
        delta[begin] += 1
        delta[end + timedelta(days=1)] -= 1
    span = (stop - start).days + 1
    step = 7 if span > 400 else 1
    values, bucket, on = [], 0, 0
    for i in range(span):
        on += delta[start + timedelta(days=i)]
        bucket = max(bucket, on)
        if (i + 1) % step == 0 or i == span - 1:
            values.append(bucket)
            bucket = 0
    peak = max(values, default=0)
    top = max(peak, 1)
    # The polyline's box is 1000 × 100; the chart stretches it to the width.
    n = max(len(values) - 1, 1)
    points = " ".join(f"{1000 * i / n:.1f},{100 - 100 * v / top:.1f}" for i, v in enumerate(values))
    ticks = []
    if span > 400:
        for y in range(start.year, stop.year + 1):
            left = (date(y, 1, 1) - start).days / span * 100
            if left >= 0:
                ticks.append({"left": round(left, 2), "label": f"’{y % 100:02d}"})
    else:
        for m in range(1, 13):
            d = date(start.year, m, 1)
            if start <= d <= stop:
                ticks.append({"left": round((d - start).days / span * 100, 2), "label": MONTHS[m - 1][0]})
    return {
        "values": ",".join(map(str, values)),
        "points": points,
        "start": start.isoformat(),
        "step": step,
        "peak": peak,
        "now": values[-1] if values else 0,
        "ticks": ticks,
        "grid": [{"v": v, "bottom": round(100 * v / top, 2)} for v in sorted({round(top / 2), top}) if v],
    }


def _durations(rows: list[Row]) -> dict:
    days = [(r.end - r.begin).days for r in rows if r.end]
    counts = [0] * len(DURATIONS)
    for d in days:
        for i, (top, _) in enumerate(DURATIONS):
            if top is None or d < top:
                counts[i] += 1
                break
    peak = max(counts, default=0)
    return {
        "bars": [{"label": DURATIONS[i][1], "n": n, "pct": round(100 * n / peak, 2) if peak else 0} for i, n in enumerate(counts)],
        "median": round(median(days)) if days else None,
        "ended": len(days),
    }


def _colors(rows: list[Row], began: str, today: date) -> list[dict]:
    counts: Counter = Counter()
    days: Counter = Counter()
    for r in rows:
        counts[r.color] += 1
        days[r.color] += ((r.end or today) - r.begin).days
    peak = max(counts.values(), default=0)
    order = {c: i for i, c in enumerate(COLOR_ORDER)}
    ranked = sorted(counts, key=lambda c: (-counts[c], order.get(c, 99)))
    return [{
        "name": c, "n": counts[c], "days": days[c],
        "pct": round(100 * counts[c] / peak, 2),
        "hex": INK_COLOR_HEX.get(c, "#333"),
        "url": usages_url(began, c),
    } for c in ranked]


def _weekdays(rows: list[Row]) -> list[dict]:
    counts = Counter(r.begin.weekday() for r in rows)
    peak = max(counts.values(), default=0)
    return [{"label": WEEKDAYS[d], "n": counts[d], "pct": round(100 * counts[d] / peak, 2) if peak else 0} for d in range(7)]


def _top(rows: list[Row], attr: str, today: date) -> list[tuple[int, int, int]]:
    fills: Counter = Counter()
    days: Counter = Counter()
    for r in rows:
        key = getattr(r, attr)
        fills[key] += 1
        days[key] += ((r.end or today) - r.begin).days
    ranked = sorted(fills, key=lambda k: (-fills[k], -days[k], k))[:TOP_N]
    return [(k, fills[k], days[k]) for k in ranked]


def _top_pens(rows: list[Row], today: date) -> list[dict]:
    top = _top(rows, "pen_id", today)
    pens = Pen.objects.select_related("brand").in_bulk([k for k, _, _ in top])
    peak = top[0][1] if top else 0
    return [{"id": k, "name": str(pens[k]), "n": n, "days": d, "pct": round(100 * n / peak, 2)} for k, n, d in top if k in pens]


def _top_inks(rows: list[Row], today: date) -> list[dict]:
    top = _top(rows, "ink_id", today)
    inks = Ink.objects.select_related("brand").in_bulk([k for k, _, _ in top])
    peak = top[0][1] if top else 0
    return [{
        "id": k, "name": str(inks[k]), "n": n, "days": d, "pct": round(100 * n / peak, 2),
        "hex": INK_COLOR_HEX.get(inks[k].color, "#333"), "bg": inks[k].swatch_bg,
    } for k, n, d in top if k in inks]


def _months_between(first: date, last: date) -> int:
    return (last.year - first.year) * 12 + last.month - first.month + 1


def build(year: int | None, today: date | None = None) -> dict:
    """Everything `/history/inkings/` draws, for one year or (None) for all."""
    today = today or date.today()
    all_rows = load_rows()
    if not all_rows:
        return {"inkings_total": 0, "chart_years": [], "scope": None}
    years = sorted({r.begin.year for r in all_rows})
    rows = [r for r in all_rows if r.begin.year == year] if year else all_rows
    first, last = years[0], max(years[-1], today.year)
    began = str(year) if year else ""

    if year:
        span_first, span_last = date(year, 1, 1), min(date(year, 12, 31), today)
        months = max(1, _months_between(span_first, span_last))
        columns = _months_columns(rows, year, today)
    else:
        span_first, span_last = min(r.begin for r in all_rows), today
        months = _months_between(span_first, span_last)
        columns = _years_columns(rows, first, last)

    durations = _durations(rows)
    return {
        "inkings_total": len(all_rows),
        "chart_years": list(reversed(years)),
        "scope": year,
        "scope_label": str(year) if year else f"{first} — {last}",
        "began": began,
        "stats": {
            "inkings": len(rows),
            "pace": round(len(rows) / months, 1),
            "median": durations["median"],
            "pens": len({r.pen_id for r in rows}),
            "inks": len({r.ink_id for r in rows}),
        },
        "columns": columns,
        "legend": _legend(rows),
        "heatmap": None if year else _heatmap(rows, first, last, today),
        # A year's line runs over all the fills, also those poured the year before.
        "desk": _desk_line(all_rows, span_first, span_last),
        "durations": durations,
        "colors": _colors(rows, began, today),
        "weekdays": _weekdays(rows),
        "top_pens": _top_pens(rows, today),
        "top_inks": _top_inks(rows, today),
    }


def year_bars(usages) -> dict | None:
    """The small chart on a pen's or an ink's page: its ink-ups per year.
    `usages` are `Usage` rows with their ink. None with fewer than two years
    to compare: one bar says nothing the count beside it does not."""
    if not usages:
        return None
    today = date.today()
    first, last = min(u.begin.year for u in usages), today.year
    if first == last:
        return None
    rows = [Row(u.begin, u.end, u.pen_id, u.ink_id, u.ink.color) for u in usages]
    per: dict[int, Counter] = defaultdict(Counter)
    for r in rows:
        per[r.begin.year][r.color] += 1
    peak = max(sum(c.values()) for c in per.values())
    cols = [_column(y, f"’{y % 100:02d}", per[y], peak, str(y)) for y in range(first, last + 1)]
    return {"columns": cols, "legend": _legend(rows)}
