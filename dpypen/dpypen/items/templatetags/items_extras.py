from django import template
from django.utils.safestring import mark_safe

from dpypen.items import lists

register = template.Library()


@register.filter
def askable(usage) -> bool:
    """An ended fill with no verdict, ended within verdicts.ASK_DAYS: a row asks
    how it wrote (README "How it wrote"). Older ones wait on the fill's form."""
    from datetime import date

    from dpypen.items import verdicts

    end = getattr(usage, "end", None)
    return bool(end and not usage.verdict and (date.today() - end).days <= verdicts.ASK_DAYS)


@register.filter
def highlight(text, terms):
    """Each search word in <mark>, through the kit's `lists.highlight`
    (KIT-LISTS): accent-folded like the search, so "zur" marks the "Zür" of
    "Zürich", longest word first, every piece escaped. `terms` is the query
    as a string or its words as a list.

    The hand-written one before it matched case but not accents, so a search
    that found "Zürich" marked nothing in it.
    """
    if not text:
        return ""
    q = " ".join(terms) if isinstance(terms, (list, tuple)) else (terms or "")
    return mark_safe(lists.highlight(text, q))


@register.filter
def json_script_safe(value):
    """JSON for a <script type="application/json"> in the page: nothing in it
    can close the tag (the river's data; no stored names in it anyway)."""
    import json

    text = json.dumps(value, separators=(",", ":"))
    return mark_safe(text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


@register.simple_tag
def kit_shell(name):
    """/kit/<name>?v=<hash>: one of the kit's cached files (kitshell.py)."""
    from dpypen.items import kitshell

    return kitshell.url(name)


@register.simple_tag
def kit_keys():
    """The end of <body>: the keyboard layer's markup, then late.js (the
    filter-nav, the shell's behaviour and the layer's script, kitshell.py)."""
    from django.utils.html import format_html
    from django.utils.safestring import mark_safe

    from dpypen.items import kitshell

    return format_html('{}\n<script src="{}"></script>', mark_safe(kitshell.KEYS_MARKUP), kitshell.url("late.js"))


@register.filter
def msgs_text(messages) -> str:
    """All of a page's messages as one line, in order: the kit shows one toast
    at a time, so a message with an Undo carries the others' words in its
    form's data-undo (a notebook import: a warning per bad row, then the Undo)."""
    return " ".join(t for t in (str(m).strip() for m in messages) if t)
