from django.http import HttpResponse

from django.core.exceptions import PermissionDenied

from dpypen.items.models import Ink, Pen
from dpypen.supen import interface


def generate(rotation, order, item):
    supen = interface(rotation=rotation, order=order, item_type=item, to_colorize=False)

    head = """<head><style>
    body { font-size: 14; white-space: pre; }
    .data a, .data span, .data tr, .data td { white-space: pre; }
    </style></head>
    """

    body = "<body><code><div class='data'>" + supen + "</div></code></body>"

    html = "<html>" + head + body + "</html>"

    return HttpResponse(html)


def supen(request, rotation, order):
    if not request.user.is_authenticated:
        raise PermissionDenied

    return generate(rotation, order, item=Pen)


def suink(request, rotation, order):
    if not request.user.is_authenticated:
        raise PermissionDenied

    return generate(rotation, order, item=Ink)
