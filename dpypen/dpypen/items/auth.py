from functools import wraps

from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone


def _is_allowed(email: str) -> bool:
    return (email or "").strip().lower() in settings.ALLOWED_EMAILS


class AllowlistAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        return _is_allowed(sociallogin.user.email)

    def pre_social_login(self, request, sociallogin):
        if not _is_allowed(sociallogin.user.email):
            raise ImmediateHttpResponse(
                HttpResponseForbidden("Not authorised. This site is private.")
            )

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        if _is_allowed(user.email):
            user.is_staff = True
            user.is_superuser = True
        return user


GUEST_SESSION_KEY = "invite_code_id"


def active_invite(request):
    """Return InviteCode if session has a valid guest invite, else None."""
    from dpypen.items.models import InviteCode
    code_id = request.session.get(GUEST_SESSION_KEY)
    if not code_id:
        return None
    try:
        code = InviteCode.objects.get(pk=code_id)
    except InviteCode.DoesNotExist:
        return None
    if not code.is_active():
        return None
    return code


def login_or_guest_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)
        invite = active_invite(request)
        if invite is not None:
            invite.visits += 1
            invite.last_seen_at = timezone.now()
            invite.save(update_fields=["visits", "last_seen_at"])
            return view(request, *args, **kwargs)
        from django.conf import settings
        login_url = getattr(settings, "LOGIN_URL", "/accounts/login/")
        return redirect(f"{login_url}?next={request.get_full_path()}")
    return wrapped


def visitor_context(request):
    """Template context processor: is_guest, is_owner."""
    is_owner = request.user.is_authenticated
    invite = None if is_owner else active_invite(request)
    return {
        "is_owner": is_owner,
        "is_guest": invite is not None,
        "can_edit": is_owner,
        "invite_label": invite.label if invite else "",
    }
