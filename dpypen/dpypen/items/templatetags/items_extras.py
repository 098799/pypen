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
