"""How it wrote: a verdict on each fill (README "How it wrote").

Until Nov 2026 the history said which ink went into which pen and for how long,
never whether the pairing was any good; the picker guessed "liked" from how often
an ink came back. A fill now carries one of three words and a short note:

    Loved      ink it again in this pen
    Fine       it wrote; nothing to remember
    Not again  it did not suit this pen (dry, feathering, stained, a hard clean)

asked at Finish (the desk, a pen's page, the inkings), and later from the desk's
"How did they write?" or the fill's form. A pairing's verdict is its latest
fill's: an opinion can change, and the newest one is what to act on.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

from django.utils import timezone

from dpypen.items.models import Usage

LOVED, FINE, NEVER = Usage.LOVED, Usage.FINE, Usage.NEVER
WORDS = {LOVED: "Loved", FINE: "Fine", NEVER: "Not again"}
# The order the buttons and the counts come in.
ORDER = (LOVED, FINE, NEVER)
# A glyph next to the word, never instead of it (the word carries the meaning).
MARKS = {LOVED: "♥", FINE: "✓", NEVER: "✕"}
# The inkings list's `?verdict=`: the three words, and "none" for a fill not said yet.
FILTERS = (*ORDER, "none")
FILTER_WORDS = {**WORDS, "none": "Not said"}

# The desk asks about a finished fill up to a year after it ended: fills end in
# batches (seven on one day in March 2026, then none for two months), so a
# shorter window would ask about nothing. Older ones wait on the inkings' "Not said".
ASK_DAYS = 365


def parse(value) -> str | None:
    """A verdict from a form, "" to clear one, None for anything else."""
    value = (value or "").strip()
    return value if value in WORDS or value == "" else None


def say(usage: Usage, verdict: str | None, note: str | None = None) -> list[str]:
    """Set the verdict (None: leave it) and the note (None: leave it) on `usage`,
    unsaved. Returns the fields that changed, verdict_at among them."""
    changed = []
    if verdict is not None and verdict != usage.verdict:
        usage.verdict = verdict
        changed.append("verdict")
    if note is not None:
        note = " ".join(note.split())[:200]
        if note != usage.note:
            usage.note = note
            changed.append("note")
    if changed:
        usage.verdict_at = timezone.now()
        changed.append("verdict_at")
    return changed


def waiting(today: date) -> int:
    """How many fills ended in the last ASK_DAYS with no verdict: the desk's
    "Just finished" asks about its own rows and links the rest."""
    return Usage.objects.filter(end__isnull=False, end__gte=today - timedelta(days=ASK_DAYS), verdict="").count()


def latest(rows) -> dict[tuple[int, int], tuple[str, date]]:
    """{(pen_id, ink_id): (verdict, its fill's begin)} from rows with pen_id,
    ink_id, begin and verdict: each pairing's newest said verdict."""
    out: dict[tuple[int, int], tuple[str, date]] = {}
    for r in rows:
        if not r.verdict:
            continue
        key = (r.pen_id, r.ink_id)
        if key not in out or r.begin >= out[key][1]:
            out[key] = (r.verdict, r.begin)
    return out


def said_rows():
    """Every fill with a verdict, as light rows (the picker and Stats)."""
    return list(Usage.objects.exclude(verdict="").values_list("pen_id", "ink_id", "begin", "end", "verdict", named=True))


@dataclass
class Shelf:
    """One pen's (or one ink's) verdicts, from its own fills: the inks (pens)
    it was loved with and the ones it should not meet again."""

    loved: list = field(default_factory=list)
    never: list = field(default_factory=list)
    said: int = 0  # fills with a verdict
    fills: int = 0  # ended fills


def shelf(usages, other: str) -> Shelf:
    """`usages`: one pen's (other="ink") or one ink's (other="pen") fills, loaded
    with that side. Each other side once, by its newest verdict; loved first by
    how often it was loved."""
    s = Shelf()
    newest: dict[int, Usage] = {}
    loves = defaultdict(int)
    for u in usages:
        if u.end is not None:
            s.fills += 1
        if not u.verdict:
            continue
        s.said += 1
        key = getattr(u, f"{other}_id")
        if u.verdict == LOVED:
            loves[key] += 1
        if key not in newest or u.begin >= newest[key].begin:
            newest[key] = u
    for key, u in newest.items():
        item = {other: getattr(u, other), "n": loves[key], "when": u.begin, "note": u.note}
        if u.verdict == LOVED:
            s.loved.append(item)
        elif u.verdict == NEVER:
            s.never.append(item)
    s.loved.sort(key=lambda i: (-i["n"], -i["when"].toordinal()))
    s.never.sort(key=lambda i: -i["when"].toordinal())
    return s
