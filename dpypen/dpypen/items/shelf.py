"""The header row's state line (kit README §4 Fleet UX "Header", PYPEN-6).

A screen's header says what the screen answers, plus how fresh that is:
"126 pens · 12 inked · last inked 2 d ago". The numbers are the collection's,
not the filter's (the list's own "1–50 of N" counts what matches), and the
freshness is the newest inking: the only thing in pypen that moves without
the owner opening a form for that very screen.

`shelf_context` hands every template a lazy `shelf`; a page that never prints
it never runs its queries (four small ones when it does: no row loops).
"""

from datetime import date

from django.db.models import Max
from django.utils.functional import SimpleLazyObject


def ago(day, today=None):
    """'today', 'yesterday', '3 d ago', '5 wk ago', '4 mo ago', '2 yr ago'."""
    if day is None:
        return ""
    n = ((today or date.today()) - day).days
    if n <= 0:
        return "today"
    if n == 1:
        return "yesterday"
    if n < 14:
        return f"{n} d ago"
    if n < 60:
        return f"{n // 7} wk ago"
    if n < 730:
        return f"{n // 30} mo ago"
    return f"{n // 365} yr ago"


class Shelf:
    def __init__(self):
        from .models import Ink, Pen, Usage

        self.pens = Pen.objects.count()
        # The same "in the cupboard" the dashboard counts: not used up, and
        # more than a sample's worth left.
        self.inks = Ink.objects.filter(used_up=False, volume__gt=5).count()
        self.inked = Usage.objects.filter(end__isnull=True).count()
        self.last = Usage.objects.aggregate(m=Max("begin"))["m"]
        self.fresh = ago(self.last)


def shelf_context(request):
    """Template context processor: `shelf`, for the owner and guests only (a
    stranger's pages print no collection numbers)."""
    return {"shelf": SimpleLazyObject(Shelf)}
