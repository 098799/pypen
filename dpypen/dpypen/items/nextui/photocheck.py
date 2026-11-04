"""Photos to check: the owner's verdict on the shots pen_photo_fill found or drew.

A machine-made photo is saved with review="check". The owner sees each one here
(and as a band on the pen's page) and says Right or Wrong. Right keeps it
(review="ok"). Wrong deletes it and blocks its source, so the next run of
pen_photo_fill tries another photo for the pen instead of the same one.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from dpypen.items import undo
from dpypen.items.models import PenPhoto, RejectedPenPhoto


def to_check():
    return PenPhoto.objects.filter(review="check")


@login_required
def check(request):
    photos = list(to_check().select_related("pen__brand").order_by("pen__brand__name", "pen__model", "pk"))
    return render(
        request,
        "next/pens/photo_check.html",
        {
            "photos": photos,
            "checked": PenPhoto.objects.filter(review="ok").count(),
            "rejected": RejectedPenPhoto.objects.count(),
            "nav": "pens",
        },
    )


@login_required
@require_POST
def verdict(request, pk, photo_pk):
    photo = get_object_or_404(PenPhoto.objects.select_related("pen__brand"), pk=photo_pk, pen_id=pk)
    pen = photo.pen
    if request.POST.get("verdict") == "wrong":
        RejectedPenPhoto.objects.create(pen=pen, source_url=photo.source_url or RejectedPenPhoto.GENERATED)
        for f in (photo.image, photo.thumbnail):
            if f:
                try:
                    f.delete(save=False)
                except Exception:  # noqa: BLE001
                    pass
        photo.clear_styled(save=False)
        photo.delete()
        undo.say(request, f"Photo of {pen} removed. The next fill tries another one.")
    else:
        photo.review = "ok"
        photo.save(update_fields=["review"])
    back = request.POST.get("next", "")
    if back and url_has_allowed_host_and_scheme(back, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(back)
    return redirect("nx_pens_photo_check")
