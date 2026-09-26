"""What to ink next: a due pen, and the inks that suit it.

The dashboard has long answered "which pen is past its turn". It never
answered the second half of the question — which ink goes in it — and that is
the half that takes the time: a hundred open bottles, each with its own rest
and its own history with the pen. This module ranks them.

Rest alone is a poor ranking for inks. On the live data (2026-09-26) every
open bottle has rested longer than its rotation's turn, the easy bottles 2.2
turns on average, so "most rested first" just lists the dustiest shelf — the
same trap the dashboard fell into with pens. Rest therefore saturates at two
turns, and the rest of the score decides between the bottles that are all
"due": a pairing this pen has never had, an ink that has been inked often (it
was liked), a colour that is not on the desk already. A bottle that is hard to
fill from goes to the bottom for a pen that fills by dipping its nib in it.
"""

import math
import random
from dataclasses import dataclass, field
from datetime import date

from django.shortcuts import get_object_or_404, render

from dpypen.items.auth import login_or_guest_required
from dpypen.items.models import Ink, Pen, Rotation, Usage

# Pens that fill by putting the nib into the bottle. A converter or an
# eyedropper barrel can be filled with a syringe, so the bottle's shape does
# not matter to them.
DIP_FILLERS = {"Piston", "Lever", "Plunger", "Bulkfiller", "Shutoff valve", "Squeeze"}
HARD_BOTTLE = "Bottle hard to fill from"

REST_CAP = 2.0  # turns of rest after which an ink is simply "due"
NEW_PAIRING = 0.4
PROVEN_PAIRING = 0.25
LOVED_PER_DOUBLING = 0.15
LOVED_CAP = 0.6
SAME_COLOUR_ON_DESK = 0.6
HARD_BOTTLE_FOR_DIPPER = 1.5

SHOWN = 6
SHUFFLE_POOL = 24


@dataclass
class Suggestion:
    ink: Ink
    score: float
    rested: int | None  # days since the ink last came out of a pen
    turns: float  # rested / its rotation's how_often
    pairings: int  # times this pen has had this ink
    last_paired: date | None
    inkings: int  # times this ink has been inked, any pen
    reasons: list[tuple[str, str]] = field(default_factory=list)  # (tone, text)


def due_pens(today, usages, rots, pens_by_rotation):
    """Pens resting past their rotation's turn, most wanted first.

    A pen is due when it has been resting longer than its rotation's
    how_often; never-inked pens in rotation are due from the day they
    arrived. Pens inked now are left out. `usages` needs only pen_id and end.
    """
    inked_now = {u.pen_id for u in usages if u.end is None}
    last_rest = {}
    for u in usages:
        if u.end is None:
            continue
        prev = last_rest.get(u.pen_id)
        if prev is None or u.end > prev:
            last_rest[u.pen_id] = u.end

    due = []
    for r in rots:
        for pen in pens_by_rotation.get(r.pk, []):
            if pen.pk in inked_now:
                continue
            rested = (today - last_rest[pen.pk]).days if pen.pk in last_rest else None
            overdue = (rested - r.how_often) if rested is not None else None
            due.append(
                {
                    "pen_id": pen.pk,
                    "pen": f"{pen.brand.name} {pen.model}" + (f" {pen.finish}" if pen.finish else ""),
                    "priority": r.priority,
                    "how_often": r.how_often,
                    "rested": rested,
                    "overdue": overdue,
                    "never": rested is None,
                }
            )
    # Ranking by "most overdue" sounded right and was exactly backwards: the
    # biggest numbers belong to pens deliberately left alone for years, so the
    # shortlist filled with the collection's dustiest corners. Priority is the
    # signal — a P0 a month past its turn matters more than a P3 five years
    # past it — so sort by priority first and only break ties on lateness.
    due.sort(key=lambda d: (d["priority"], not d["never"], -(d["overdue"] if d["overdue"] is not None else 0)))
    return [d for d in due if d["never"] or (d["overdue"] or 0) > 0]


def _pen_rotations():
    return list(Rotation.objects.filter(in_use=True, whos="Tomek", priority__in=[0, 1, 2, 3]).order_by("priority"))


def _span(days):
    if days < 60:
        return f"{days} days"
    if days < 730:
        return f"{round(days / 30.4)} months"
    return f"{days / 365.25:.1f} years".replace(".0 ", " ")


def suggest_inks(pen, today, usages):
    """Every open bottle, scored for `pen`, best first.

    `usages` is every inking, with pen_id, ink_id, begin and end.
    """
    inks = list(Ink.objects.filter(used_up=False, volume__gt=5, rotation__in_use=True).select_related("brand", "rotation"))

    last_end, inkings, inked_now = {}, {}, set()
    pairs, pair_last = {}, {}
    desk_colours = set()
    ink_colour = {i.pk: i.color for i in inks}
    for u in usages:
        inkings[u.ink_id] = inkings.get(u.ink_id, 0) + 1
        if u.end is None:
            inked_now.add(u.ink_id)
            if u.ink_id in ink_colour:
                desk_colours.add(ink_colour[u.ink_id])
        elif last_end.get(u.ink_id) is None or u.end > last_end[u.ink_id]:
            last_end[u.ink_id] = u.end
        if u.pen_id == pen.pk:
            pairs[u.ink_id] = pairs.get(u.ink_id, 0) + 1
            if pair_last.get(u.ink_id) is None or u.begin > pair_last[u.ink_id]:
                pair_last[u.ink_id] = u.begin
    # A sample or a used-up bottle on the desk is not a candidate, but its
    # colour is still on the desk.
    elsewhere = inked_now - set(ink_colour)
    if elsewhere:
        desk_colours |= set(Ink.objects.filter(pk__in=elsewhere).values_list("color", flat=True))

    dipper = pen.filling in DIP_FILLERS
    out = []
    for ink in inks:
        if ink.pk in inked_now:
            continue
        since = last_end.get(ink.pk) or ink.obtained
        rested = (today - since).days if since else None
        turn = ink.rotation.how_often if ink.rotation.how_often > 0 else 365
        turns = rested / turn if rested is not None else REST_CAP
        s = Suggestion(
            ink=ink,
            score=0.0,
            rested=rested,
            turns=turns,
            pairings=pairs.get(ink.pk, 0),
            last_paired=pair_last.get(ink.pk),
            inkings=inkings.get(ink.pk, 0),
        )

        s.score += min(turns, REST_CAP)
        if ink.pk not in last_end and ink.pk not in inkings:
            s.reasons.append(("good", "never inked"))
        elif turns >= 1:
            s.reasons.append(("good", f"resting {_span(rested)}"))
        else:
            s.reasons.append(("", f"out {_span(rested)} ago"))

        if s.pairings:
            s.score += PROVEN_PAIRING
            times = "once" if s.pairings == 1 else f"{s.pairings}×"
            s.reasons.append(("", f"in this pen {times}, last {s.last_paired:%b %Y}"))
        else:
            s.score += NEW_PAIRING
            s.reasons.append(("good", "new pairing"))

        if s.inkings >= 3:
            s.score += min(LOVED_CAP, LOVED_PER_DOUBLING * math.log2(1 + s.inkings))
            s.reasons.append(("good", f"a favourite · {s.inkings} inkings"))

        if ink.color in desk_colours:
            s.score -= SAME_COLOUR_ON_DESK
            s.reasons.append(("warn", f"{ink.color.lower()} is on the desk"))

        if dipper and ink.rotation.whos == HARD_BOTTLE:
            s.score -= HARD_BOTTLE_FOR_DIPPER
            s.reasons.append(("warn", f"hard bottle for a {pen.filling.lower()} filler"))

        out.append(s)

    out.sort(key=lambda s: (-s.score, s.ink.brand.name, s.ink.name))
    return out


def pick(ranked, shuffle):
    """The top few, or a seeded draw from a wider pool of good ones."""
    if not shuffle:
        return ranked[:SHOWN]
    pool = ranked[:SHUFFLE_POOL]
    chosen = random.Random(shuffle).sample(pool, min(SHOWN, len(pool)))
    return sorted(chosen, key=lambda s: -s.score)


@login_or_guest_required
def next_inking(request):
    """Choose a pen that is due, then an ink for it."""
    today = date.today()
    usages = list(Usage.objects.only("pen_id", "ink_id", "begin", "end"))

    rots = _pen_rotations()
    pens_by_rotation = {}
    for p in Pen.objects.filter(rotation__in=rots).select_related("brand").order_by("brand__name", "model"):
        pens_by_rotation.setdefault(p.rotation_id, []).append(p)
    due = due_pens(today, usages, rots, pens_by_rotation)

    pen_id = request.GET.get("pen", "")
    if pen_id.isdigit():
        pen = get_object_or_404(Pen.objects.select_related("brand", "rotation"), pk=int(pen_id))
    elif due:
        pen = Pen.objects.select_related("brand", "rotation").get(pk=due[0]["pen_id"])
    else:
        pen = None

    shuffle = request.GET.get("shuffle", "")
    shuffle = int(shuffle) if shuffle.isdigit() else 0

    suggestions, inked_now = [], None
    if pen is not None:
        current = [u for u in usages if u.pen_id == pen.pk and u.end is None]
        if current:
            inked_now = Usage.objects.select_related("ink__brand").get(pk=current[0].pk)
        suggestions = pick(suggest_inks(pen, today, usages), shuffle)

    return render(
        request,
        "items/next.html",
        {
            "due": due,
            "pen": pen,
            "pen_in_due": pen is not None and any(d["pen_id"] == pen.pk for d in due),
            "inked_now": inked_now,
            "suggestions": suggestions,
            "shuffle": shuffle,
            "next_shuffle": shuffle + 1,
        "pool": SHUFFLE_POOL,
            "dipper": pen is not None and pen.filling in DIP_FILLERS,
            "nav": "next",
        },
    )
