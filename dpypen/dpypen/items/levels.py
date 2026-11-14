"""Ink left: about how much is in each bottle (README "Ink left").

The app knew each bottle's size and every fill drawn from it, and never put the
two together: a 1 ml sample looked as full after three fills as a new 50 ml
bottle. A fill takes about one pen's worth: `Pen.fill_ml` when the owner said
it, else the usual for its filling (FILL_ML). What is left is the bottle's
volume less every fill, or, once the owner has looked at the bottle (`Ink.level_ml`
on `Ink.level_on`), that look less the fills begun after it.

It is an estimate and says so ("about"): a long fill was topped up, a converter
was not filled to the brim. The owner's look corrects it, and "Empty" is the
same as Used up.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from django.db.models import Case, F, FloatField, OuterRef, Q, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce, Greatest

from dpypen.items.models import Ink, Usage

# One fill from the bottle, in ml, per filling system. A converter takes
# 0.5-1.0 ml, a piston 1.0-2.0, an eyedropper barrel 2-3. Shutoff valve and
# bulk fillers are pistons with a bigger barrel.
FILL_ML = {
    "c/c": 0.8,
    "Piston": 1.4,
    "Plunger": 1.5,
    "Bulkfiller": 1.6,
    "Shutoff valve": 1.6,
    "Lever": 1.0,
    "Squeeze": 0.9,
    "Eyedropper": 2.5,
}
DEFAULT_FILL = 1.0
# Running low: fewer fills left than this, at the ink's usual fill.
LOW_FILLS = 2
# Under this an estimate says "probably empty".
EMPTY_ML = 0.3
# The ink's pace: ml a year over the last three years (or since it came).
PACE_YEARS = 3

# What the owner can say after a look, and the share of the bottle it means.
LOOKS = (
    ("full", "Full", 1.0),
    ("3/4", "¾", 0.75),
    ("1/2", "½", 0.5),
    ("1/4", "¼", 0.25),
    ("low", "Nearly out", 0.08),
    ("empty", "Empty", 0.0),
)
LOOK = {k: share for k, _, share in LOOKS}


def pen_fill(pen) -> float:
    """How much one fill of `pen` takes, in ml."""
    return float(pen.fill_ml) if pen.fill_ml else FILL_ML.get(pen.filling, DEFAULT_FILL)


def usual_fill(filling: str) -> float:
    return FILL_ML.get(filling, DEFAULT_FILL)


def ml(v: float) -> str:
    """A volume as one says it: 0.8, 2.4, 24."""
    if v < 10:
        s = f"{v:.1f}"
        return s[:-2] if s.endswith(".0") else s
    return f"{round(v):,}"


@dataclass
class Level:
    volume: int
    left: float  # ml, never below 0
    drawn: float  # ml drawn by every fill, all time
    fills: int  # fills drawn from it, all time
    fill: float  # one usual fill from it, ml
    pace: float  # ml a year, lately
    checked: date | None  # the owner's last look
    used_up: bool

    @property
    def pct(self) -> int:
        if self.used_up or not self.volume:
            return 0
        return max(0, min(100, round(100 * self.left / self.volume)))

    @property
    def fills_left(self) -> int:
        return 0 if self.used_up else int(self.left // self.fill) if self.fill else 0

    @property
    def empty(self) -> bool:
        """Probably empty, not marked so."""
        return not self.used_up and self.left < EMPTY_ML

    @property
    def low(self) -> bool:
        """Running low: fewer than LOW_FILLS fills left (empty ones too)."""
        return not self.used_up and self.left < LOW_FILLS * self.fill

    @property
    def left_words(self) -> str:
        """The short form: "about 24 ml", "about a fill", "probably empty"."""
        if self.used_up:
            return "used up"
        if self.empty:
            return "probably empty"
        n = self.fills_left
        if n <= 1:
            return "about a fill" if n == 1 else "under a fill"
        return f"about {ml(self.left)} ml"

    @property
    def words(self) -> str:
        """The sentence: "About 24 ml left of 30, some 30 fills"."""
        if self.used_up:
            return "Used up"
        if self.empty:
            return "Probably empty"
        n = self.fills_left
        if n < 1:
            return f"Under a fill left, about {ml(self.left)} ml"
        if n == 1:
            return f"About one fill left, {ml(self.left)} ml"
        return f"About {ml(self.left)} ml left of {self.volume}, some {n} fills"

    @property
    def row_words(self) -> str:
        """A list row's: "about 24 of 30 ml left", "1 ml, probably empty"."""
        if self.used_up:
            return f"{self.volume} ml, used up"
        if self.empty:
            return f"{self.volume} ml, probably empty"
        n = self.fills_left
        if n <= 1:
            return f"{self.volume} ml, {'about a fill' if n == 1 else 'under a fill'} left"
        if self.left >= self.volume - 0.05:
            return f"{self.volume} ml, full"
        return f"about {ml(self.left)} of {self.volume} ml left"

    @property
    def years_left(self) -> float | None:
        """At its pace, how many years until it is empty; None with no pace."""
        if self.used_up or self.pace <= 0 or self.left <= 0:
            return None
        return self.left / self.pace

    @property
    def lasts(self) -> str | None:
        y = self.years_left
        if y is None:
            return None
        if y < 1:
            months = max(1, round(y * 12))
            return f"about {months} month{'s' if months != 1 else ''}"
        if y >= 100:
            return "over a hundred years"
        return f"about {round(y)} year{'s' if round(y) != 1 else ''}"


def _rows(ink_ids):
    """(ink_id, begin, filling, fill_ml) of every fill from these inks: one query."""
    return Usage.objects.filter(ink_id__in=ink_ids).values_list("ink_id", "begin", "pen__filling", "pen__fill_ml")


def for_inks(inks, today: date | None = None, rows=None) -> dict[int, Level]:
    """{ink pk: Level} for `inks`, from one query over their fills (or `rows`,
    as `_rows` gives them)."""
    today = today or date.today()
    inks = list(inks)
    if not inks:
        return {}
    by_ink = defaultdict(list)
    for ink_id, begin, filling, fill_ml in (rows if rows is not None else _rows([i.pk for i in inks])):
        by_ink[ink_id].append((begin, float(fill_ml) if fill_ml else usual_fill(filling)))
    return {i.pk: level(i, by_ink.get(i.pk, []), today) for i in inks}


def level(ink, fills, today: date) -> Level:
    """One ink's Level from its fills, [(begin, ml)]."""
    drawn = sum(m for _, m in fills)
    if ink.level_ml is not None and ink.level_on:
        left = ink.level_ml - sum(m for b, m in fills if b > ink.level_on)
    else:
        left = ink.volume - drawn
    # The usual fill: the median of its last five, so a sample that only ever
    # went into converters is measured in converters.
    recent = sorted(fills)[-5:]
    fill = sorted(m for _, m in recent)[len(recent) // 2] if recent else DEFAULT_FILL
    since = today - timedelta(days=round(365.25 * PACE_YEARS))
    start = max(since, ink.obtained) if ink.obtained else since
    years = max(1.0, (today - start).days / 365.25)
    pace = sum(m for b, m in fills if b >= start) / years
    return Level(
        volume=ink.volume,
        left=max(0.0, left),
        drawn=drawn,
        fills=len(fills),
        fill=fill,
        pace=pace,
        checked=ink.level_on,
        used_up=bool(ink.used_up),
    )


def attach(inks, today: date | None = None):
    """Put each ink's Level on it as `.lvl`; returns the inks."""
    inks = list(inks)
    got = for_inks(inks, today)
    for i in inks:
        i.lvl = got.get(i.pk)
    return inks


# ---- in SQL, for a list's order -----------------------------------------


def fill_sql(prefix: str = "pen__"):
    """One fill of the pen at `prefix`, in ml, as an SQL expression."""
    usual = Case(
        *[When(**{prefix + "filling": k}, then=Value(v)) for k, v in FILL_ML.items()], default=Value(DEFAULT_FILL), output_field=FloatField()
    )
    return Coalesce(F(prefix + "fill_ml"), usual, output_field=FloatField())


def left_sql():
    """What `level` computes, as an annotation on Ink: the list's "Least left"
    order runs in SQL, so paging keeps it (kit §14)."""

    def drawn(extra):
        return Coalesce(
            Subquery(
                Usage.objects.filter(Q(ink=OuterRef("pk")) & extra).order_by().values("ink").annotate(s=Sum(fill_sql())).values("s")[:1],
                output_field=FloatField(),
            ),
            Value(0.0),
        )

    after_look = drawn(Q(begin__gt=OuterRef("level_on")))
    every = drawn(Q())
    return Case(
        When(used_up=True, then=Value(0.0)),
        When(level_ml__isnull=False, level_on__isnull=False, then=Greatest(F("level_ml") - after_look, Value(0.0))),
        default=Greatest(F("volume") - every, Value(0.0)),
        output_field=FloatField(),
    )


# ---- the owner's look ---------------------------------------------------


def look(ink: Ink, key: str, today: date) -> list[str] | None:
    """Set the bottle's level from a look (LOOKS), unsaved; "forget" drops the
    look and goes back to the estimate. Empty marks it used up; a level on a
    used-up bottle takes the mark off. Returns the changed fields, None for a
    key it does not know."""
    if key == "forget":
        ink.level_ml, ink.level_on = None, None
        return ["level_ml", "level_on"]
    if key not in LOOK:
        return None
    share = LOOK[key]
    ink.level_ml = round(share * ink.volume, 2)
    ink.level_on = today
    fields = ["level_ml", "level_on"]
    if share == 0:
        ink.used_up = True
        ink.used_up_when = ink.used_up_when or today
        fields += ["used_up", "used_up_when"]
    elif ink.used_up:
        ink.used_up, ink.used_up_when = False, None
        fields += ["used_up", "used_up_when"]
    return fields


def running_low(today: date | None = None) -> list:
    """The inks running low, the emptiest first: not used up, drawn from at
    least once (a sample nobody opened is not news), a bottle in a rotation in
    use or any sample (the samples sit in a rotation of their own, not in use)."""
    inks = list(Ink.objects.filter(Q(rotation__in_use=True) | Q(volume__lte=5)).exclude(used_up=True)
                .select_related("brand"))
    got = for_inks(inks, today)
    low = [i for i in inks if got[i.pk].low and got[i.pk].fills]
    for i in low:
        i.lvl = got[i.pk]
    low.sort(key=lambda i: (i.lvl.left / (i.lvl.fill or 1), i.brand.name, i.name, i.pk))
    return low

