import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def highlight(text, terms):
    """Wrap each search-term occurrence in <mark>. Terms may be a list or space-separated string."""
    if not text:
        return ""
    escaped = escape(str(text))
    if not terms:
        return mark_safe(escaped)
    if isinstance(terms, str):
        terms = terms.split()
    unique = sorted({t for t in terms if t}, key=len, reverse=True)
    if not unique:
        return mark_safe(escaped)
    pattern = "|".join(re.escape(t) for t in unique)
    result = re.sub(f"({pattern})", r"<mark>\1</mark>", escaped, flags=re.IGNORECASE)
    return mark_safe(result)


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
