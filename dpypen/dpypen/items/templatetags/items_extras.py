import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def highlight(text, terms):
    """Wrap each search-term occurrence in <mark>. Terms may be a list or space-separated string.

    The terms are matched in the stored text and each piece is escaped on its
    own. Matching in the escaped text instead found "amp" or "lt" inside
    &amp; and &lt; and cut the entity in two, so a search for "lt" printed
    "&<mark>lt</mark>;" where the name had a "<".
    """
    if not text:
        return ""
    text = str(text)
    if isinstance(terms, str):
        terms = terms.split()
    unique = sorted({t for t in (terms or []) if t}, key=len, reverse=True)
    if not unique:
        return mark_safe(escape(text))
    pattern = re.compile("(" + "|".join(re.escape(t) for t in unique) + ")", re.IGNORECASE)
    parts = pattern.split(text)
    # split() with one group: even indexes are the text between, odd the hits.
    return mark_safe(
        "".join(f"<mark>{escape(p)}</mark>" if i % 2 else escape(p) for i, p in enumerate(parts))
    )


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
