from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET

from dpypen.items.auth import GUEST_SESSION_KEY
from dpypen.items.models import InviteCode


@require_GET
def activate(request, token):
    code = get_object_or_404(InviteCode, token=token)
    if not code.is_active():
        messages.error(request, "This invite link is no longer valid.")
        return redirect("home")
    request.session[GUEST_SESSION_KEY] = code.pk
    request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days
    return redirect("dashboard")


@require_GET
def deactivate(request):
    request.session.pop(GUEST_SESSION_KEY, None)
    return redirect("home")
