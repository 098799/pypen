"""What the new version's Stats screens draw (PYPEN-11).

Plain numbers for the templates, from the same rows the old History uses: a few
hundred inkings, kept per worker for four minutes under a key that changes with
the data. The charts are drawn on the server, HTML and SVG, with no library
(README "Inking charts"); `static/items/next/next.js` reads them under a finger.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from calendar import monthrange
from datetime import date, timedelta
from statistics import median

from django.core.cache import cache
from django.db.models import Count, F, Max
from django.urls import reverse

from dpypen.items import history, inkings, pairing
from dpypen.items.inkings import COLOR_ORDER, MONTHS
from dpypen.items.models import Ink, Pen, Rotation, Usage
from dpypen.items.nextui import color as ink_color
from dpypen.items.public import INK_COLOR_HEX

# Boxes of a chart's SVG. The chart stretches them to its width.
RIVER_W, RIVER_H = 1000, 280

# ---- the cache -----------------------------------------------------------


def _stamp() -> str:
    u = Usage.objects.aggregate(n=Count("pk"), last=Max("pk"), began=Max("begin"), ended=Max("end"))
    p = Pen.objects.aggregate(n=Count("pk"), last=Max("pk"))
    i = Ink.objects.aggregate(n=Count("pk"), last=Max("pk"))
    return f"{date.today()}:{u['n']}:{u['last']}:{u['began']}:{u['ended']}:{p['n']}:{p['last']}:{i['n']}:{i['last']}"


def cached(kind: str, fn):
    key = f"next:{kind}:{_stamp()}"
    data = cache.get(key)
    if data is None:
        data = fn()
        cache.set(key, data, 240)
    return data


# ---- small helpers ---------------------------------------------------------


def pln(money) -> float:
    return history._pln(money)


def span(days: int) -> str:
    """A length of time, as one would say it."""
    if days < 14:
        return f"{days} day{'' if days == 1 else 's'}"
    if days < 60:
        return f"{round(days / 7)} weeks"
    if days < 700:
        return f"{round(days / 30.4)} months"
    return f"{days / 365.25:.1f} years".replace(".0 ", " ")


def bars(counts: Counter | dict, top: int | None = None, other: str = "Other") -> list[dict]:
    """A ranked list of labelled numbers; what falls under `top` folds into one row."""
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], str(kv[0])))
    if top and len(ranked) > top:
        rest = sum(v for _, v in ranked[top:])
        ranked = ranked[:top] + [(other, rest)]
    peak = max((v for _, v in ranked), default=0) or 1
    return [{"label": k, "n": round(v) if isinstance(v, float) else v, "pct": round(100 * v / peak, 2)} for k, v in ranked]


def columns(rows: list[tuple]) -> list[dict]:
    """[(label, value, title)] as columns on one axis."""
    peak = max((v for _, v, _ in rows), default=0) or 1
    return [{"label": a, "n": round(v) if isinstance(v, float) else v, "pct": round(100 * v / peak, 2), "title": t} for a, v, t in rows]


def load() -> list:
    return list(Usage.objects.annotate(color=F("ink__color")).values_list("begin", "end", "pen_id", "ink_id", "color", "nib_id", named=True))


# ---- the river -------------------------------------------------------------


def river(rows, today: date) -> dict | None:
    """Every fill since the first, as colour: how many pens held each ink colour,
    month by month, stacked. One shape per colour, in the real ink colour."""
    if not rows:
        return None
    first = min(r.begin for r in rows)
    months = []
    y, m = first.year, first.month
    while (y, m) <= (today.year, today.month):
        months.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    index = {ym: i for i, ym in enumerate(months)}
    order = [c for c in COLOR_ORDER if c in INK_COLOR_HEX] + [c for c in INK_COLOR_HEX if c not in COLOR_ORDER]
    place = {c: i for i, c in enumerate(order)}
    grid = [[0.0] * len(months) for _ in order]

    for r in rows:
        begin, end = r.begin, r.end or today
        c = place.get(r.color)
        if c is None or end < begin:
            continue
        y, m = begin.year, begin.month
        while (y, m) <= (end.year, end.month):
            ndays = monthrange(y, m)[1]
            lo, hi = max(begin, date(y, m, 1)), min(end, date(y, m, ndays))
            i = index.get((y, m))
            if i is not None:
                # The month still running counts its days so far.
                base = today.day if (y, m) == (today.year, today.month) else ndays
                grid[c][i] += ((hi - lo).days + 1) / base
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)

    totals = [sum(col[i] for col in grid) for i in range(len(months))]

    # The shape is smoothed over three months (a finger still reads the month as
    # it was): a fill that starts mid-month is no event, and raw it was all spikes.
    last = len(months) - 1
    raw, grid = grid, [
        [(col[max(i - 1, 0)] + 2 * col[i] + col[min(i + 1, last)]) / 4 for i in range(len(months))]
        for col in grid
    ]
    peak = max(sum(col[i] for col in grid) for i in range(len(months))) or 1
    n = max(len(months) - 1, 1)
    x = lambda i: round(RIVER_W * i / n)  # noqa: E731
    y_of = lambda v: round(RIVER_H - RIVER_H * v / peak, 1)  # noqa: E731

    shapes, floor = [], [0.0] * len(months)
    for c, name in enumerate(order):
        vals = grid[c]
        tops = [floor[i] + vals[i] for i in range(len(months))]
        # Only where the colour is: a path through its long zero stretches is
        # weight for nothing.
        parts, i = [], 0
        while i < len(months):
            if vals[i] <= 0:
                i += 1
                continue
            a = max(i - 1, 0)
            b = i
            while b + 1 < len(months) and vals[b + 1] > 0:
                b += 1
            b = min(b + 1, len(months) - 1)
            up = [f"{x(k)},{y_of(tops[k])}" for k in range(a, b + 1)]
            down = [f"{x(k)},{y_of(floor[k])}" for k in range(b, a - 1, -1)]
            parts.append("M" + " ".join(up + down) + "Z")
            i = b + 1
        floor = tops
        if parts:
            shapes.append({"name": name, "hex": INK_COLOR_HEX[name], "d": "".join(parts), "i": c})

    used = Counter(r.color for r in rows)
    total_fills = sum(used.values()) or 1
    legend = [{"name": k, "hex": INK_COLOR_HEX.get(k, "#333"), "n": used[k], "share": round(100 * used[k] / total_fills)}
              for k in sorted(used, key=lambda c: -used[c])]
    ticks = [{"left": round(100 * i / n, 2), "label": str(ym[0])} for i, ym in enumerate(months) if ym[1] == 1]
    return {
        "shapes": shapes,
        "w": RIVER_W, "h": RIVER_H,
        "peak": round(peak, 1),
        "ticks": ticks,
        "legend": legend,
        # What a finger reads: one row a month, [month, total, [colour index, pens]...]
        "data": {
            "colors": order,
            "months": [[f"{MONTHS[ym[1] - 1]} {ym[0]}", round(totals[i], 1),
                        [[c, round(raw[c][i], 1)] for c in range(len(order)) if raw[c][i] >= 0.05]]
                       for i, ym in enumerate(months)],
        },
    }


# ---- overview --------------------------------------------------------------


def first_pairs(rows) -> set:
    """The rows that were the first time this pen met this ink."""
    seen, firsts = set(), set()
    for i, r in sorted(enumerate(rows), key=lambda t: (t[1].begin, t[0])):
        pair = (r.pen_id, r.ink_id)
        if pair not in seen:
            seen.add(pair)
            firsts.add(i)
    return firsts


def _same_period(rows, year: int, today: date, pens, inks, firsts) -> dict:
    """A year's numbers up to today's date in that year, so a year still running
    compares fairly with the one before."""
    try:
        stop = today.replace(year=year)
    except ValueError:  # 29 Feb
        stop = today.replace(year=year, day=28)
    start = date(year, 1, 1)
    picked = [(i, r) for i, r in enumerate(rows) if start <= r.begin <= stop]
    ended = [(r.end - r.begin).days for _, r in picked if r.end]
    new_pens = [p for p in pens if p.obtained and start <= p.obtained <= stop]
    new_inks = [i for i in inks if i.obtained and start <= i.obtained <= stop]
    return {
        "inkings": len(picked),
        "pens": len({r.pen_id for _, r in picked}),
        "inks": len({r.ink_id for _, r in picked}),
        "new_pairs": sum(1 for i, _ in picked if i in firsts),
        "fill": round(median(ended)) if ended else None,
        "bought": len(new_pens),
        "bottles": len(new_inks),
        "spent": round(sum(pln(p.price) for p in new_pens)),
    }


def _on_desk_days(rows, today: date):
    """(pens held per day as a Counter of day -> pens, first day)."""
    delta: Counter = Counter()
    for r in rows:
        delta[r.begin] += 1
        delta[(r.end or today) + timedelta(days=1)] -= 1
    return delta


def _dry_and_peak(rows, today: date) -> dict:
    delta = _on_desk_days(rows, today)
    day, last_day = min(delta), today
    on, peak, peak_day, dry, longest, longest_end = 0, 0, day, 0, 0, None
    while day <= last_day:
        on += delta[day]
        if on > peak:
            peak, peak_day = on, day
        if on <= 0:
            dry += 1
            if dry > longest:
                longest, longest_end = dry, day
        else:
            dry = 0
        day += timedelta(days=1)
    return {"peak": peak, "peak_day": peak_day, "dry": longest, "dry_end": longest_end}


def overview() -> dict:
    today = date.today()
    rows = load()
    if not rows:
        return {"empty": True}
    pens = list(Pen.objects.only("obtained", "price", "price_currency"))
    inks = list(Ink.objects.only("obtained", "volume", "used_up"))
    firsts = first_pairs(rows)
    this_year = today.year

    a = _same_period(rows, this_year, today, pens, inks, firsts)
    b = _same_period(rows, this_year - 1, today, pens, inks, firsts)
    labels = (
        ("inkings", "Inkings"),
        ("pens", "Pens used"),
        ("inks", "Inks used"),
        ("new_pairs", "New pairings"),
        ("fill", "Typical fill, days"),
        ("bought", "Pens added"),
        ("bottles", "Inks added"),
        ("spent", "Spent on pens, PLN"),
    )
    versus = []
    for key, label in labels:
        x, y = a[key], b[key]
        delta = None if x is None or y is None else x - y
        versus.append({"label": label, "now": x if x is not None else "–", "then": y if y is not None else "–",
                       "delta": delta, "up": bool(delta and delta > 0), "down": bool(delta and delta < 0)})

    first = min(r.begin for r in rows)
    ended = [(r.end - r.begin).days for r in rows if r.end]
    desk = _dry_and_peak(rows, today)
    longest = max((r for r in rows if r.end), key=lambda r: (r.end - r.begin).days, default=None)
    pen_days: Counter = Counter()
    for r in rows:
        pen_days[r.pen_id] += ((r.end or today) - r.begin).days
    return {
        "river": river(rows, today),
        "inkings": len(rows),
        "since": first,
        "tracked": span((today - first).days),
        "pens_used": len({r.pen_id for r in rows}),
        "pens_total": len(pens),
        "inks_used": len({r.ink_id for r in rows}),
        "inks_total": len(inks),
        "pairs": len(firsts),
        "pace": round(len(rows) / max(1, inkings._months_between(first, today)), 1),
        "fill_median": round(median(ended)) if ended else None,
        "fill_long": max(ended, default=0),
        "ink_years": round(sum(pen_days.values()) / 365.25, 1),
        "now": sum(1 for r in rows if not r.end),
        "peak": desk["peak"],
        "peak_day": desk["peak_day"],
        "dry": desk["dry"],
        "dry_end": desk["dry_end"],
        "longest_days": (longest.end - longest.begin).days if longest else 0,
        "year": this_year,
        "last_year": this_year - 1,
        "versus": versus,
        "by_year": columns([(f"’{y['year'] % 100:02d}", y["days"],
                             f"{y['year']}: {y['days']:,} pen-days, {y['inkings']} inkings, {y['pens']} pens, {y['inks']} inks")
                            for y in history._overview_data()["year_list"]]),
    }


# ---- inkings: the habits under the charts ----------------------------------


def habits() -> dict:
    today = date.today()
    rows = load()
    if not rows:
        return {}
    firsts = first_pairs(rows)
    per_month = Counter(r.begin.month for r in rows)
    seasons = columns([(MONTHS[m - 1][0], per_month[m], MONTHS[m - 1]) for m in range(1, 13)])
    new_by_year, all_by_year, fills_by_year = Counter(), Counter(), defaultdict(list)
    for i, r in enumerate(rows):
        all_by_year[r.begin.year] += 1
        if i in firsts:
            new_by_year[r.begin.year] += 1
        if r.end:
            fills_by_year[r.begin.year].append((r.end - r.begin).days)
    years = list(range(min(all_by_year), today.year + 1))
    explore = columns([(f"’{y % 100:02d}", round(100 * new_by_year[y] / all_by_year[y]) if all_by_year[y] else 0,
                        f"{y}: {new_by_year[y]} new of {all_by_year[y]}") for y in years])
    fill_trend = columns([(f"’{y % 100:02d}", round(median(fills_by_year[y])) if fills_by_year[y] else 0,
                           str(y)) for y in years])
    # Nibs, weighted by how often they were inked.
    from dpypen.items.models import Nib

    nibs = {n.pk: n for n in Nib.objects.all()}
    width, cut, material = Counter(), Counter(), Counter()
    for r in rows:
        n = nibs.get(r.nib_id)
        if n:
            width[n.width or "Not noted"] += 1
            cut[n.cut or "Not noted"] += 1
            material[n.material or "Steel"] += 1
    return {
        "seasons": seasons,
        "explore": explore,
        "fill_trend": fill_trend,
        "nib_width": bars(width, top=8),
        "nib_cut": bars(cut),
        "nib_material": bars(material),
    }


# ---- collection ------------------------------------------------------------

PRICE_BANDS = ((200, "Under 200"), (500, "200–500"), (1000, "500–1,000"), (2000, "1,000–2,000"), (None, "2,000 and up"))
# `CH` means both Swiss and Chinese in constants.NATIONALITIES: the brand decides.
SWISS_BRANDS = {"Caran d'Ache", "Caran d’Ache", "Carandache", "Caran Dache"}
COUNTRY = {"US": "USA", "EN": "England", "FR": "France", "DE": "Germany", "IT": "Italy", "JP": "Japan", "TW": "Taiwan", "PL": "Poland"}


def _country(brand) -> str:
    if brand.nationality == "CH":
        return "Switzerland" if brand.name in SWISS_BRANDS else "China"
    return COUNTRY.get(brand.nationality, brand.nationality or "Unknown")


def _scatter(points: list[dict]) -> dict:
    """Price against days inked. Price on a log scale: 20 and 4,000 PLN share a
    collection. Days on a root scale: most pens have few."""
    import math

    if not points:
        return {"points": [], "xticks": [], "yticks": []}
    lo, hi = max(10, min(p["price"] for p in points)), max(p["price"] for p in points)
    top = max((p["days"] for p in points), default=1) or 1
    lx0, lx1 = math.log10(lo), math.log10(max(hi, lo * 2))
    sx = lambda v: round(100 * (math.log10(max(v, lo)) - lx0) / (lx1 - lx0), 2)  # noqa: E731
    sy = lambda v: round(100 * math.sqrt(v / top), 2)  # noqa: E731
    out = [{**p, "x": sx(p["price"]), "y": sy(p["days"])} for p in points]
    xticks = [{"x": sx(v), "label": f"{v:,}"} for v in (50, 100, 200, 500, 1000, 2000, 5000, 10000) if lo <= v <= hi]
    yticks = [{"y": sy(v), "label": str(v)} for v in (100, 500, 1000, 2000, 4000) if v <= top]
    return {"points": out, "xticks": xticks, "yticks": yticks}


def collection() -> dict:
    today = date.today()
    pens = list(Pen.objects.select_related("brand", "rotation"))
    if not pens:
        return {"empty": True}
    rows = load()
    days, fills = Counter(), Counter()
    for r in rows:
        days[r.pen_id] += ((r.end or today) - r.begin).days
        fills[r.pen_id] += 1

    brands, countries, filling, age, bands = Counter(), Counter(), Counter(), Counter(), Counter()
    priced, by_year_n, by_year_pln = [], Counter(), Counter()
    for p in pens:
        brands[p.brand.name] += 1
        countries[_country(p.brand)] += 1
        filling[p.filling] += 1
        age[p.age] += 1
        price = pln(p.price)
        if p.obtained:
            by_year_n[p.obtained.year] += 1
            by_year_pln[p.obtained.year] += price
        if price:
            priced.append((p, price))
            for top, label in PRICE_BANDS:
                if top is None or price < top:
                    bands[label] += 1
                    break
    prices = [v for _, v in priced]
    ink_spend = sum(pln(i.price) for i in Ink.objects.only("price", "price_currency"))
    years = list(range(min(by_year_n), today.year + 1)) if by_year_n else []
    running, cumulative = 0, []
    for y in years:
        running += by_year_n[y]
        cumulative.append((f"’{y % 100:02d}", running, f"{y}: {running} pens"))

    points, value = [], []
    for p, price in priced:
        d = days[p.pk]
        name = str(p)
        points.append({"name": name, "price": round(price), "days": d, "fills": fills[p.pk],
                       "url": reverse("nx_pens_detail", args=[p.pk])})
        value.append({"name": name, "url": reverse("nx_pens_detail", args=[p.pk]), "price": round(price), "days": d,
                      "per_day": price / d if d else None})
    earning = sorted((v for v in value if v["days"] >= 30), key=lambda v: v["per_day"])[:6]
    waiting = sorted((v for v in value if v["days"] < 30), key=lambda v: -v["price"])[:6]
    for v in earning:
        v["cost"] = f"{v['per_day']:.2f}" if v["per_day"] < 10 else f"{v['per_day']:.0f}"

    return {
        "pens": len(pens),
        "brands_n": len(brands),
        "brands": bars(brands, top=10),
        "countries": bars(countries),
        "filling": bars(filling),
        "age": bars(age),
        "bands": [{"label": label, "n": bands[label],
                   "pct": round(100 * bands[label] / (max(bands.values()) or 1), 2)} for _, label in PRICE_BANDS],
        "spent": f"{round(sum(prices)):,}",
        "ink_spent": f"{round(ink_spend):,}",
        "typical": f"{round(median(prices)):,}" if prices else "0",
        "dearest": f"{round(max(prices)):,}" if prices else "0",
        "per_year": columns([(f"’{y % 100:02d}", by_year_n[y], f"{y}: {by_year_n[y]} pens") for y in years]),
        "spend_year": columns([(f"’{y % 100:02d}", by_year_pln[y], f"{y}: {round(by_year_pln[y]):,} PLN") for y in years]),
        "cumulative": columns(cumulative),
        "scatter": _scatter(points),
        "earning": earning,
        "waiting": waiting,
    }


# ---- cupboard --------------------------------------------------------------


def cupboard() -> dict:
    today = date.today()
    inks = list(Ink.objects.select_related("brand", "rotation"))
    if not inks:
        return {"empty": True}
    rows = load()
    fills, last_end, in_pen = Counter(), {}, set()
    color_fills: Counter = Counter()
    for r in rows:
        fills[r.ink_id] += 1
        color_fills[r.color] += 1
        if r.end is None:
            in_pen.add(r.ink_id)
        elif r.ink_id not in last_end or r.end > last_end[r.ink_id]:
            last_end[r.ink_id] = r.end
    open_inks = [i for i in inks if not i.used_up and i.volume > 5]
    samples = [i for i in inks if not i.used_up and i.volume <= 5]
    used = [i for i in inks if i.used_up]

    bottles: Counter = Counter(i.color for i in open_inks)
    ml: Counter = Counter()
    for i in open_inks:
        ml[i.color] += i.volume
    wall = sorted(open_inks, key=lambda i: ink_color.spectrum_key(ink_color.ink_hex(i, INK_COLOR_HEX)))
    spectrum = [{"name": str(i), "bg": i.swatch_bg, "url": reverse("nx_inks_detail", args=[i.pk]), "color": i.color,
                 "fills": fills[i.pk]} for i in wall]

    total_b, total_f = sum(bottles.values()) or 1, sum(color_fills.values()) or 1
    share = []
    for c in sorted(set(bottles) | set(color_fills), key=lambda c: -color_fills[c]):
        own, use = round(100 * bottles[c] / total_b, 1), round(100 * color_fills[c] / total_f, 1)
        share.append({"name": c, "hex": INK_COLOR_HEX.get(c, "#333"), "own": own, "use": use,
                      "bottles": bottles[c], "fills": color_fills[c], "ml": ml[c],
                      "lo": min(own, use), "gap": abs(own - use), "more": use >= own})
    scale = max((max(s["own"], s["use"]) for s in share), default=1) or 1
    for s in share:
        s["own_x"], s["use_x"] = round(100 * s["own"] / scale, 2), round(100 * s["use"] / scale, 2)
        s["lo_x"], s["gap_x"] = min(s["own_x"], s["use_x"]), abs(s["own_x"] - s["use_x"])

    never = sorted((i for i in open_inks if not fills[i.pk]), key=lambda i: i.obtained or today)
    resting = []
    for i in open_inks:
        if i.pk in in_pen or not fills[i.pk] or i.pk not in last_end:
            continue
        resting.append({"ink": i, "days": (today - last_end[i.pk]).days})
    resting.sort(key=lambda r: -r["days"])
    for r in resting:
        r["span"] = span(r["days"])

    brands = Counter(i.brand.name for i in open_inks)
    how = Counter(i.how for i in inks)
    # Every ink by the year it came, used up ones too (the old History's two charts).
    got_n, got_pln = Counter(), Counter()
    for i in inks:
        if i.obtained:
            got_n[i.obtained.year] += 1
            got_pln[i.obtained.year] += pln(i.price)
    got_years = list(range(min(got_n), today.year + 1)) if got_n else []
    return {
        "ink_year": columns([(f"’{y % 100:02d}", got_n[y], f"{y}: {got_n[y]} ink{'s' if got_n[y] != 1 else ''}") for y in got_years]),
        "ink_spend_year": columns([(f"’{y % 100:02d}", got_pln[y], f"{y}: {round(got_pln[y]):,} PLN") for y in got_years]),
        "bottles": len(open_inks),
        "ml": f"{sum(i.volume for i in open_inks):,}",
        "samples": len(samples),
        "used_up": len(used),
        "never_n": len(never),
        "in_pen": len(in_pen),
        "spectrum": spectrum,
        "share": share,
        "share_scale": round(scale),
        "never": never[:8],
        "resting": resting[:8],
        "brands": bars(brands, top=8),
        "how": bars(how),
    }


# ---- rotation --------------------------------------------------------------


def rotation() -> dict:
    today = date.today()
    usages = list(Usage.objects.only("pen_id", "ink_id", "begin", "end"))
    rots = pairing._pen_rotations()
    pens_by_rot = defaultdict(list)
    for p in Pen.objects.filter(rotation__in=rots).select_related("brand").order_by("brand__name", "model"):
        pens_by_rot[p.rotation_id].append(p)

    by_pen = defaultdict(list)
    for u in usages:
        by_pen[u.pen_id].append(u)
    groups = []
    for r in rots:
        inked = within = overdue = never = 0
        gaps = []
        for p in pens_by_rot[r.pk]:
            mine = sorted(by_pen[p.pk], key=lambda u: u.begin)
            for a, b in zip(mine, mine[1:]):
                if a.end:
                    gaps.append(max(0, (b.begin - a.end).days))
            if any(u.end is None for u in mine):
                inked += 1
            elif not mine:
                never += 1
            else:
                rested = (today - max(u.end for u in mine)).days
                if rested > r.how_often:
                    overdue += 1
                else:
                    within += 1
        n = inked + within + overdue + never or 1
        segments = [
            {"key": "inked", "label": "Inked", "n": inked, "pct": round(100 * inked / n, 2)},
            {"key": "within", "label": "Resting in turn", "n": within, "pct": round(100 * within / n, 2)},
            {"key": "over", "label": "Past their turn", "n": overdue, "pct": round(100 * overdue / n, 2)},
            {"key": "never", "label": "Never inked", "n": never, "pct": round(100 * never / n, 2)},
        ]
        groups.append({
            "priority": r.priority, "turn": r.how_often, "turn_words": span(r.how_often), "n": n,
            "segments": [s for s in segments if s["n"]],
            "gap": span(round(median(gaps))) if gaps else None,
            "on_time": round(100 * (inked + within) / n),
        })

    due = pairing.due_pens(today, usages, rots, pens_by_rot)
    for d in due:
        d["span"] = span(d["rested"]) if d["rested"] is not None else None
        d["late"] = span(d["overdue"]) if d["overdue"] else None
    per_year = sum(1 for u in usages if u.begin >= today - timedelta(days=365))
    in_rotation = sum(len(v) for v in pens_by_rot.values())

    # The bottles' two turns: how many have been out of a pen longer.
    last_end, in_pen = {}, set()
    for u in usages:
        if u.end is None:
            in_pen.add(u.ink_id)
        elif u.ink_id not in last_end or u.end > last_end[u.ink_id]:
            last_end[u.ink_id] = u.end
    bottle_rows = []
    for rot in Rotation.objects.filter(in_use=True).exclude(whos__in=["Tomek", "Ozlem"]).order_by("priority"):
        inks = list(Ink.objects.filter(rotation=rot, used_up=False, volume__gt=5))
        late = 0
        for i in inks:
            since = last_end.get(i.pk) or i.obtained
            if i.pk not in in_pen and since and (today - since).days > rot.how_often:
                late += 1
        if inks:
            bottle_rows.append({"name": rot.whos, "turn": span(rot.how_often), "n": len(inks), "late": late,
                                "pct": round(100 * late / len(inks))})
    return {
        "groups": groups,
        "due": due[:12],
        "due_n": len(due),
        "in_rotation": in_rotation,
        "per_year": per_year,
        "round_years": round(in_rotation / per_year, 1) if per_year else None,
        "bottle_rows": bottle_rows,
    }


# ---- calendar, timeline, pairs (the old History's numbers) -----------------


def calendar_year(year: int | None) -> dict:
    """One year as twelve small months. The old page's one strip of 53 weeks
    leaves a phone 6 px a day; a month block has room for a colour."""
    data = cached("calendar", history._calendar_data)
    years = data["calendar_years"]
    if not years:
        return {"years": [], "cal": None}
    chosen = next((c for c in years if c["year"] == year), years[-1])
    by_month: dict[int, list] = defaultdict(list)
    for week in chosen["weeks"]:
        for d in week:
            if d:
                by_month[d["date"].month].append(d)
    months = []
    for m in sorted(by_month):
        days = sorted(by_month[m], key=lambda d: d["date"])
        months.append({"name": MONTHS[m - 1], "blanks": range(days[0]["date"].weekday()), "days": days})
    return {"years": [c["year"] for c in reversed(years)], "cal": chosen, "cal_year": chosen["year"], "months": months}


def pairs() -> dict:
    today = date.today()
    rows = load()
    days, n = Counter(), Counter()
    for r in rows:
        key = (r.pen_id, r.ink_id)
        n[key] += 1
        days[key] += ((r.end or today) - r.begin).days
    ranked = sorted(n, key=lambda k: (-n[k], -days[k]))[:10]
    pens = Pen.objects.select_related("brand").in_bulk({k[0] for k in ranked})
    inks = Ink.objects.select_related("brand").in_bulk({k[1] for k in ranked})
    best = [{"pen": pens[k[0]], "ink": inks[k[1]], "n": n[k], "days": days[k]} for k in ranked if k[0] in pens and k[1] in inks]
    data = cached("matrix", history._matrix_data)
    return {**data, "best": best, "pairs_n": len(n), "repeat_n": sum(1 for k in n if n[k] > 1)}


def rebase(value):
    """Links made for the old pages (/prev/), pointing at their twins (the
    charts of `inkings.build`: "See them", "The year's charts")."""
    if isinstance(value, str):
        return value.replace("/prev/history/inkings/", "/stats/inkings/").replace("/prev/", "/")
    if isinstance(value, list):
        return [rebase(v) for v in value]
    if isinstance(value, dict):
        return {k: rebase(v) for k, v in value.items()}
    return value
