from django import template
from django.utils.safestring import mark_safe

from dpypen.items import lists

register = template.Library()


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
