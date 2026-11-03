"""What the new version's shell needs on every page: the ink it wears."""

from django.utils.functional import SimpleLazyObject

from dpypen.items import skin
from dpypen.items.models import Usage
from dpypen.items.nextui import color
from dpypen.items.public import INK_COLOR_HEX


def _accent():
    """The app's accent is the newest ink on the desk with a colour to it, so
    the app changes with what is in the pens. A black or a grey has none to lend."""
    for u in Usage.objects.filter(end__isnull=True).select_related("ink").order_by("-begin", "-pk")[:12]:
        hex_ = color.ink_hex(u.ink, INK_COLOR_HEX)
        if color.chromatic(hex_):
            return {**color.accent(hex_), "ink": str(u.ink.name)}
    return {**color.accent(None), "ink": ""}


def next_ui(request):
    if not skin.is_next(request):
        return {}
    return {"nx_accent": SimpleLazyObject(_accent)}
