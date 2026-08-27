"""Toast-sized undo for the handful of actions that are easy to fat-finger.

Every mutation worth taking back leaves a snapshot in the session — the whole
object as Django's own serializer sees it, taken *before* the change — and a
token. The toast carries the token; posting it back re-saves the snapshot (or
deletes the row, for an undone create). Session storage means the offer dies
with the browser session, which is the right lifetime for "wait, no".
"""

import logging
import secrets

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

SESSION_KEY = "undo_stack"
STACK_MAX = 8       # a toast is a short memory; no need to keep more


def _stack(request):
    return request.session.get(SESSION_KEY) or []


def _push(request, record):
    stack = _stack(request)
    stack.append(record)
    request.session[SESSION_KEY] = stack[-STACK_MAX:]
    request.session.modified = True


def snapshot(obj):
    """Freeze an object's current state so it can be restored later."""
    return serializers.serialize("json", [obj])


def offer(request, message, *, kind, model=None, pk=None, frozen=None):
    """Show `message` as a toast with an Undo button attached.

    kind="create": undo deletes the row identified by model/pk.
    kind="update"/"delete": undo re-saves `frozen` (see snapshot()).
    """
    token = secrets.token_urlsafe(9)
    record = {"token": token, "kind": kind}
    if kind == "create":
        record["model"] = f"{model._meta.app_label}.{model._meta.model_name}"
        record["pk"] = pk
    else:
        record["frozen"] = frozen
    _push(request, record)
    messages.success(request, message, extra_tags=f"undo:{token}")


def say(request, message):
    """A toast with nothing to take back."""
    messages.success(request, message)


@login_required
@require_POST
def undo(request, token):
    stack = _stack(request)
    record = next((r for r in stack if r["token"] == token), None)
    if record is None:
        messages.info(request, "That undo has expired.")
        return _back(request)

    request.session[SESSION_KEY] = [r for r in stack if r["token"] != token]
    request.session.modified = True

    try:
        with transaction.atomic():
            if record["kind"] == "create":
                model = apps.get_model(record["model"])
                model.objects.filter(pk=record["pk"]).delete()
            else:
                for wrapped in serializers.deserialize("json", record["frozen"]):
                    wrapped.save()
    except Exception:
        logger.exception("undo failed for %s", record.get("kind"))
        messages.error(request, "Could not undo that.")
        return _back(request)

    messages.info(request, "Undone.")
    return _back(request)


def _back(request):
    nxt = request.POST.get("next") or request.META.get("HTTP_REFERER")
    # Only ever bounce back inside this site.
    if nxt and nxt.startswith("/") and not nxt.startswith("//"):
        return redirect(nxt)
    return redirect(reverse("dashboard"))
