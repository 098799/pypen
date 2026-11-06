"""The `supen` and `suink` tables of the terminal, as a page (PYPEN-12).

`dpypen/supen.py` prints, per rotation, every pen (or open bottle) with how many
fills it had, how many days it spent inked, and how many days since its last
fill ended, coloured against the rotation's turn. This is the same table, from
one query over the inkings, never one per row.

The colours are supen's `colorize`: within three quarters of the turn green,
up to five quarters amber, past that red. A pen inked now is 0 days, a pen
never inked sorts last, as `math.inf` does there.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from dpypen.items.models import Ink, Pen, Rotation, Usage

# (key, chip label, sort key per row). Each runs the way supen's -o does:
# smallest first, so the pens that were inked last sit at the top.
SORTS = (
    ("last", "Last inked"),
    ("fills", "Fills"),
    ("days", "Days inked"),
    ("name", "Name"),
)
SORT_KEYS = {k for k, _ in SORTS}

INK_ROTATIONS = ("Bottle easy to fill from", "Bottle hard to fill from")


def _state(since, turn: int) -> str:
    """supen's colorize, as a word for the CSS."""
    if since is None:
        return "never"
    if since == 0:
        return "now"
    if turn <= 0:
        return "off"
    if since <= turn * 3 / 4:
        return "fresh"
    if since <= turn * 5 / 4:
        return "due"
    return "late"


def pen_groups() -> list[dict]:
    """The pen rotations supen knows, highest priority first: Tomek's P0 to P3,
    then Ozlem's. A rotation with no pens is left out. Then supen's `-r out`, the
    pens taken out of rotation: a chip of its own, not part of All, as in supen."""
    rots = list(Rotation.objects.filter(in_use=True, whos="Tomek", priority__isnull=False).order_by("priority"))
    rots += list(Rotation.objects.filter(in_use=True, whos="Ozlem"))
    groups = []
    for r in rots:
        if r.whos == "Tomek":
            groups.append({"key": f"p{r.priority}", "chip": f"P{r.priority}", "title": f"Priority {r.priority}", "rot": r})
        else:
            groups.append({"key": r.whos.lower(), "chip": f"{r.whos}'s", "title": f"{r.whos}'s", "rot": r})
    out = Rotation.objects.filter(whos="Tomek", priority__isnull=True).first()
    if out:
        groups.append({"key": "out", "chip": "Out", "title": "Out of rotation", "rot": out, "solo": True})
    return groups


def ink_groups() -> list[dict]:
    by_name = {r.whos: r for r in Rotation.objects.filter(whos__in=INK_ROTATIONS, in_use=True)}
    out = []
    for name, key, title in (
        (INK_ROTATIONS[0], "easy", "Easy to fill from"),
        (INK_ROTATIONS[1], "hard", "Hard to fill from"),
    ):
        if name in by_name:
            out.append({"key": key, "chip": title, "title": title, "rot": by_name[name]})
    return out


def _rows(items, field: str, usages, today: date, turn: int, sort: str) -> list[dict]:
    mine = defaultdict(list)
    for u in usages:
        mine[getattr(u, field)].append(u)
    rows = []
    for it in items:
        us = mine.get(it.pk, [])
        open_ = [u for u in us if u.end is None]
        if open_:
            since = 0
        elif us:
            since = (today - max(u.end for u in us)).days
        else:
            since = None
        rows.append(
            {
                "item": it,
                "fills": len(us),
                "days": sum(((u.end or today) - u.begin).days for u in us),
                "since": since,
                "state": _state(since, turn),
                # what it is inked with now (a pen) or what holds it now (an ink)
                "now": open_,
            }
        )

    def by_last(r):
        return (r["since"] is None, r["since"] or 0, str(r["item"]).lower())

    keyf = {
        "last": by_last,
        "fills": lambda r: (r["fills"], by_last(r)),
        "days": lambda r: (r["days"], by_last(r)),
        "name": lambda r: str(r["item"]).lower(),
    }[sort]
    rows.sort(key=keyf)
    return rows


def build(kind: str, rot: str = "", sort: str = "last", today: date | None = None) -> dict:
    """`kind` is "pens" (supen) or "inks" (suink). `rot` narrows to one group by
    its chip key; an unknown one is no filter. `sort` is one of SORTS."""
    today = today or date.today()
    if sort not in SORT_KEYS:
        sort = "last"
    groups = pen_groups() if kind == "pens" else ink_groups()
    if rot not in {g["key"] for g in groups}:
        rot = ""
    shown = [g for g in groups if g["key"] == rot or (not rot and not g.get("solo"))]

    if kind == "pens":
        field = "pen_id"
        usages = list(Usage.objects.select_related("ink__brand"))
        items = defaultdict(list)
        for p in Pen.objects.filter(rotation__in=[g["rot"] for g in shown]).select_related("brand"):
            items[p.rotation_id].append(p)
    else:
        field = "ink_id"
        usages = list(Usage.objects.select_related("pen__brand"))
        items = defaultdict(list)
        # suink's bottles: open ones with more than a few ml left
        for i in Ink.objects.filter(rotation__in=[g["rot"] for g in shown], volume__gt=5, used_up=False).select_related("brand"):
            items[i.rotation_id].append(i)

    out = []
    for g in shown:
        r = g["rot"]
        rows = _rows(items.get(r.pk, []), field, usages, today, r.how_often, sort)
        if not rows:
            continue
        counts = defaultdict(int)
        for row in rows:
            counts[row["state"]] += 1
        out.append(
            {
                "key": g["key"],
                "title": g["title"],
                "turn": r.how_often,
                "rows": rows,
                "n": len(rows),
                "inked": counts["now"],
                "late": counts["late"],
                "never": counts["never"],
            }
        )
    return {
        "kind": kind,
        "groups": out,
        "chips": [("", "All")] + [(g["key"], g["chip"]) for g in groups],
        "rot": rot,
        "sort": sort,
        "sorts": SORTS,
        "total": sum(g["n"] for g in out),
    }
