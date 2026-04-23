from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_http_methods

from dpypen.items.auth import GUEST_SESSION_KEY
from dpypen.items.models import InviteCode


@require_http_methods(["GET", "POST"])
def activate(request, token):
    code = get_object_or_404(InviteCode, token=token)
    if not code.is_active():
        messages.error(request, "This invite link is no longer valid.")
        return redirect("home")
    if request.method == "POST":
        request.session.cycle_key()
        request.session[GUEST_SESSION_KEY] = code.pk
        request.session.set_expiry(60 * 60 * 24 * 30)
        return redirect("dashboard")
    return render(request, "items/invite_accept.html", {"code": code})


@require_POST
def deactivate(request):
    request.session.pop(GUEST_SESSION_KEY, None)
    return redirect("home")
