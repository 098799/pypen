from collections import Counter
from datetime import date, timedelta

from django.shortcuts import render

from dpypen.items.auth import login_or_guest_required
from dpypen.items.models import Brand, Ink, Pen, Usage, WritingSample
from dpypen.items.public import INK_COLOR_HEX


@login_or_guest_required
def records(request):
    today = date.today()

    pens = list(Pen.objects.select_related("brand"))
    inks = list(Ink.objects.select_related("brand"))
    usages = list(Usage.objects.select_related("pen__brand", "ink__brand", "nib"))

    pen_lookup = {p.pk: p for p in pens}
    ink_lookup = {i.pk: i for i in inks}

    pen_days: dict[int, int] = {}
    pen_fills: Counter = Counter()
    pen_distinct_inks: dict[int, set[int]] = {}
    ink_days: dict[int, int] = {}
    ink_fills: Counter = Counter()
    ink_distinct_pens: dict[int, set[int]] = {}

    longest_fill = None  # the single longest inking
    shortest_fill = None
    for u in usages:
        days = ((u.end or today) - u.begin).days
        pen_days[u.pen_id] = pen_days.get(u.pen_id, 0) + days
        pen_fills[u.pen_id] += 1
        pen_distinct_inks.setdefault(u.pen_id, set()).add(u.ink_id)
        ink_days[u.ink_id] = ink_days.get(u.ink_id, 0) + days
        ink_fills[u.ink_id] += 1
        ink_distinct_pens.setdefault(u.ink_id, set()).add(u.pen_id)

        if u.end is not None:
            if not longest_fill or days > longest_fill["days"]:
                longest_fill = {"u": u, "days": days}
            if not shortest_fill or days < shortest_fill["days"]:
                shortest_fill = {"u": u, "days": days}

    cards = []

    def pen_card(title, subtitle, pen, extra=None, color=None):
        cards.append({
            "title": title, "subtitle": subtitle,
            "primary": str(pen),
            "link": ("pen", pen.pk),
            "extra": extra, "color": color,
        })

    def ink_card(title, subtitle, ink, extra=None):
        cards.append({
            "title": title, "subtitle": subtitle,
            "primary": str(ink),
            "link": ("ink", ink.pk),
            "extra": extra,
            "color": INK_COLOR_HEX.get(ink.color, "#333"),
            "bg": ink.swatch_bg,
        })

    # Workhorse
    if pen_days:
        pid, d = max(pen_days.items(), key=lambda kv: kv[1])
        pen_card("Workhorse pen", "most days inked", pen_lookup[pid], extra=f"{d} days across {pen_fills[pid]} fills")

    # Most refilled
    if pen_fills:
        pid, n = pen_fills.most_common(1)[0]
        pen_card("Most-refilled pen", "greatest number of fill events", pen_lookup[pid], extra=f"{n} fills")

    # Most inks tried
    if pen_distinct_inks:
        pid = max(pen_distinct_inks, key=lambda p: len(pen_distinct_inks[p]))
        n = len(pen_distinct_inks[pid])
        pen_card("Most curious pen", "the most different inks poured in", pen_lookup[pid], extra=f"{n} distinct inks")

    # Loyalist (≥3 fills, fewest distinct inks)
    loyal_candidates = [
        (pid, len(inks_set)) for pid, inks_set in pen_distinct_inks.items()
        if pen_fills[pid] >= 3
    ]
    if loyal_candidates:
        pid, n = min(loyal_candidates, key=lambda kv: (kv[1], -pen_fills[kv[0]]))
        pen_card("Loyalist", "most fills, fewest different inks", pen_lookup[pid], extra=f"{pen_fills[pid]} fills, only {n} ink{'s' if n != 1 else ''}")

    # Priciest (converted to PLN for comparison)
    # Approximate rates to PLN (base) — good enough for ranking.
    TO_PLN = {
        "PLN": 1.0, "EUR": 4.3, "USD": 4.0, "GBP": 5.0, "CHF": 4.6,
        "JPY": 0.027, "CAD": 2.9, "AUD": 2.6, "SEK": 0.38, "CZK": 0.17,
    }
    def _pln(money):
        if not money or not money.amount:
            return None
        code = str(money.currency.code) if hasattr(money.currency, "code") else str(money.currency)
        r = TO_PLN.get(code)
        if r is None:
            return None
        return float(money.amount) * r

    with_price = [(p, _pln(p.price)) for p in pens if _pln(p.price) is not None]
    if with_price:
        priciest, pln = max(with_price, key=lambda kv: kv[1])
        extra = f"{priciest.price}"
        if str(priciest.price.currency) != "PLN":
            extra += f" (~{pln:,.0f} PLN)"
        pen_card("Priciest", "most expensive pen acquired", priciest, extra=extra)

    # Oldest in collection
    oldest = min((p for p in pens if p.obtained), key=lambda p: p.obtained, default=None)
    if oldest:
        pen_card("Cornerstone", "earliest pen in the collection", oldest, extra=f"obtained {oldest.obtained:%b %Y}")

    # Newest arrival
    newest = max((p for p in pens if p.obtained), key=lambda p: p.obtained, default=None)
    if newest:
        pen_card("Latest arrival", "newest pen", newest, extra=f"obtained {newest.obtained:%b %Y}")

    # Longest single fill
    if longest_fill:
        u = longest_fill["u"]
        cards.append({
            "title": "Longest sojourn",
            "subtitle": "single ink, in one pen, uninterrupted",
            "primary": f"{u.pen} · {u.ink}",
            "link": ("pen", u.pen_id),
            "extra": f"{longest_fill['days']} days — {u.begin:%b %Y} → {u.end:%b %Y}",
            "color": INK_COLOR_HEX.get(u.ink.color, "#333"),
            "bg": u.ink.swatch_bg,
        })

    # Beloved ink
    if ink_days:
        iid, d = max(ink_days.items(), key=lambda kv: kv[1])
        ink_card("Beloved ink", "most days on the page", ink_lookup[iid], extra=f"{d} days across {ink_fills[iid]} fills")

    # Most versatile ink (used in most pens)
    if ink_distinct_pens:
        iid = max(ink_distinct_pens, key=lambda i: len(ink_distinct_pens[i]))
        n = len(ink_distinct_pens[iid])
        ink_card("Traveler ink", "poured into the most different pens", ink_lookup[iid], extra=f"tried in {n} pens")

    # Most-refilled ink
    if ink_fills:
        iid, n = ink_fills.most_common(1)[0]
        ink_card("Most-refilled ink", "greatest number of fill events", ink_lookup[iid], extra=f"{n} fills")

    # Biggest brand (pens)
    brand_pen = Counter(p.brand.name for p in pens)
    if brand_pen:
        b, n = brand_pen.most_common(1)[0]
        cards.append({
            "title": "Biggest maker",
            "subtitle": "most pens of a single brand",
            "primary": b,
            "extra": f"{n} pens",
        })

    # Biggest brand (inks)
    brand_ink = Counter(i.brand.name for i in inks)
    if brand_ink:
        b, n = brand_ink.most_common(1)[0]
        cards.append({
            "title": "Biggest ink house",
            "subtitle": "most bottles from a single ink maker",
            "primary": b,
            "extra": f"{n} bottles",
        })

    # Most pens simultaneously inked on a single day
    day_counts: Counter = Counter()
    for u in usages:
        end = u.end or today
        cur = u.begin
        while cur <= end:
            day_counts[cur] += 1
            cur += timedelta(days=1)
            if (cur - u.begin).days > 2000:
                break
    if day_counts:
        peak_day, peak_n = day_counts.most_common(1)[0]
        cards.append({
            "title": "Peak desk day",
            "subtitle": "most pens inked at once",
            "primary": peak_day.strftime("%b %-d, %Y"),
            "extra": f"{peak_n} pens on duty that day",
        })

    # Writing samples captured
    ws_total = WritingSample.objects.count()
    ws_clean = WritingSample.objects.exclude(image_clean="").count()
    if ws_total:
        cards.append({
            "title": "Writing samples",
            "subtitle": "captured specimens",
            "primary": f"{ws_total}",
            "extra": f"{ws_clean} cleaned with AI",
        })

    # Used up inks count
    used_up_inks = Ink.objects.filter(used_up=True).count()
    if used_up_inks:
        cards.append({
            "title": "Emptied bottles",
            "subtitle": "inks that ran out",
            "primary": f"{used_up_inks}",
            "extra": f"of {len(inks)} bottles",
        })

    # Oldest ink still around
    oldest_ink = min((i for i in inks if i.obtained and not i.used_up and i.volume > 5), key=lambda i: i.obtained, default=None)
    if oldest_ink:
        ink_card("Elder ink", "oldest active ink in the cupboard", oldest_ink, extra=f"obtained {oldest_ink.obtained:%b %Y}")

    return render(request, "items/records.html", {
        "cards": cards,
        "nav": "records",
    })
