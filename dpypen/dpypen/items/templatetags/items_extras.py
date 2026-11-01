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


_KIT_THEME_JS = None


@register.simple_tag
def kit_theme_js():
    """The kit's theme.js (templates/items/_theme.js), inlined as it is.

    Read as a file, not with {% include %}: the snippet's header comment holds
    an include tag of its own, which the template engine would execute.
    """
    global _KIT_THEME_JS
    if _KIT_THEME_JS is None:
        from pathlib import Path

        path = Path(__file__).resolve().parent.parent / "templates" / "items" / "_theme.js"
        _KIT_THEME_JS = path.read_text(encoding="utf-8")
    return mark_safe(_KIT_THEME_JS)
