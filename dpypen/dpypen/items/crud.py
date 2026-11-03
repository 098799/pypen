import logging
import re
from datetime import date

from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.core.files.base import ContentFile
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from dpypen.items import inkindex, inkings, listing, penindex, undo
from dpypen.items.auth import login_or_guest_required
from dpypen.items.forms import InkForm, PenForm, UsageForm
from dpypen.items.models import BadImage, Ink, InkSwatch, Pen, PenPhoto, Usage, WritingSample
from dpypen.items.public import INK_COLOR_HEX

logger = logging.getLogger(__name__)


# ----- Usages -----

USAGE_ROWS = ("pen__brand", "ink__brand", "nib")


BEGAN = re.compile(r"([1-9]\d{3})(?:-(0[1-9]|1[0-2]))?")


def usage_scope(request):
    """{"began", "color", "label"}: the part of the inkings a chart's mark
    opens (`?began=2024` or `2024-08`, `?color=Blue`). A value that is no such
    thing is no filter (kit §4), so the list shows what is really on."""
    m = BEGAN.fullmatch(request.GET.get("began", ""))
    began = m.group(0) if m else ""
    color = request.GET.get("color", "")
    if color not in INK_COLOR_HEX:
        color = ""
    words = []
    if color:
        words.append(color)
    if m:
        words.append(date(int(m.group(1)), int(m.group(2)), 1).strftime("%b %Y") if m.group(2) else m.group(1))
    return {"began": began, "color": color, "label": " · ".join(words)}


def usage_search(request):
    """(queryset, q): the inkings the search keeps (/usages/, /api/usages)."""
    q = (request.GET.get("q") or "").strip()
    qs = listing.search(Usage.objects.select_related(*USAGE_ROWS), q, listing.USAGE_FIELDS)
    scope = usage_scope(request)
    if scope["began"]:
        y, _, mo = scope["began"].partition("-")
        qs = qs.filter(begin__year=int(y))
        if mo:
            qs = qs.filter(begin__month=int(mo))
    if scope["color"]:
        qs = qs.filter(ink__color=scope["color"])
    return qs, q


def usage_rows(request):
    """(active, past, q) for /usages/, searched."""
    qs, q = usage_search(request)
    return qs.filter(end__isnull=True), qs.filter(end__isnull=False), q


@login_or_guest_required
def usages_list(request):
    """The pens on the desk (all of them: no more than there are pens), then
    the past inkings newest first, 50 at a time (kit §14, PYPEN-7). They were
    40 to a numbered page; Load more suits a phone."""
    limit, offset = listing.page_args(request)
    today = date.today()
    active_qs, past_qs, q = usage_rows(request)
    more_only = listing.is_more(request)
    active = [] if (offset or more_only) else list(
        active_qs.prefetch_related("pen__photos").order_by("-begin", "-pk"))
    total = past_qs.count()
    past, _ = listing.window(past_qs.order_by("-begin", "-pk"), offset, limit)

    for u in active:
        u.days = (today - u.begin).days
        u.ink_hex = INK_COLOR_HEX.get(u.ink.color, "#333")
        u.ink_bg = u.ink.swatch_bg
        photos = list(u.pen.photos.all()[:1])
        u.photo_url = photos[0].grid_url if photos else None
    for u in past:
        u.days = (u.end - u.begin).days
        u.ink_hex = INK_COLOR_HEX.get(u.ink.color, "#333")
        u.ink_bg = u.ink.swatch_bg

    partial = more_only or (request.headers.get("HX-Request") and not request.headers.get("HX-Boosted"))
    template = "items/usages/_content.html" if partial else "items/usages/list.html"
    return listing.vary(render(request, template, {
        "active": active,
        "past": past,
        # The heading opens the list; a Load more answer continues it.
        "past_head": not more_only,
        "total": total,
        "query": q,
        "scope": usage_scope(request),
        "more": listing.more(request, offset, limit, total),
        "nav": "usages",
    }))


@login_required
def usages_create(request):
    initial = {}
    if request.method == "GET":
        pen_id = request.GET.get("pen")
        ink_id = request.GET.get("ink")
        nib_id = request.GET.get("nib")
        if pen_id and pen_id.isdigit(): initial["pen"] = int(pen_id)
        if ink_id and ink_id.isdigit(): initial["ink"] = int(ink_id)
        if nib_id and nib_id.isdigit(): initial["nib"] = int(nib_id)
    form = UsageForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        usage = form.save()
        undo.offer(request, f"Inked {usage.pen} with {usage.ink}.",
                   kind="create", model=Usage, pk=usage.pk)
        return redirect("pens_detail", pk=usage.pen_id)
    return render(request, "items/usages/form.html", {
        "form": form,
        "title": "New inking",
        "submit_label": "Ink it",
        "nav": "usages",
    })


@login_required
def usages_edit(request, pk):
    usage = get_object_or_404(Usage, pk=pk)
    before = undo.snapshot(Usage.objects.get(pk=pk)) if request.method == "POST" else None
    form = UsageForm(request.POST or None, instance=usage)
    if request.method == "POST" and form.is_valid():
        form.save()
        undo.offer(request, f"Saved {usage.pen} · {usage.ink}.",
                   kind="update", frozen=before)
        return redirect("usages_list")
    return render(request, "items/usages/form.html", {
        "form": form,
        "usage": usage,
        "samples": list(usage.samples.all()),
        "title": f"Edit inking · {usage.pen}",
        "submit_label": "Save",
        "nav": "usages",
    })


@login_required
@require_POST
def usages_end(request, pk):
    usage = get_object_or_404(Usage, pk=pk)
    before = undo.snapshot(usage)
    usage.end = date.today()
    usage.save(update_fields=["end"])
    undo.offer(request, f"Finished {usage.pen} · {usage.ink}.",
               kind="update", frozen=before)
    return redirect("usages_list")


@login_required
@require_POST
def usages_delete(request, pk):
    usage = get_object_or_404(Usage, pk=pk)
    # The samples cascade with the inking, so they ride along in the snapshot;
    # their image files are left on disk, which is what makes this restorable.
    frozen = serializers.serialize("json", [usage, *usage.samples.all()])
    label = f"{usage.pen} · {usage.ink}"
    usage.delete()
    undo.offer(request, f"Deleted {label}.", kind="delete", frozen=frozen)
    return redirect("usages_list")


def _save_uploads(request, files, make):
    """Each uploaded file through `make`; one that is not a readable photo is
    named in a message and skipped, so the others still go in (PYPEN-4: it
    was a 500 that lost the whole batch)."""
    from django.contrib import messages

    made, bad = [], []
    for f in files:
        try:
            made.append(make(f))
        except BadImage as exc:
            logger.warning("upload %r is not a readable photo: %s", f.name, exc)
            bad.append((f.name or "file")[:60])
    if bad:
        messages.error(request, "Not a photo this app can read, so not added: " + ", ".join(bad)
                       + ". JPEG, PNG or WebP works.")
    return made


@login_required
@require_POST
def usages_sample_add(request, pk):
    usage = get_object_or_404(Usage, pk=pk)
    _save_uploads(request, request.FILES.getlist("image"),
                  lambda f: WritingSample.objects.create(usage=usage, image=f))
    return redirect("usages_edit", pk=pk)


@login_required
@require_POST
def samples_extract(request, pk):
    from django.contrib import messages

    from dpypen.items.enhance import generate_writing_sample

    sample = get_object_or_404(WritingSample, pk=pk)
    sample.image.open("rb")
    try:
        src = sample.image.read()
    finally:
        sample.image.close()
    try:
        cleaned = generate_writing_sample(src, mime_type="image/jpeg")
    except Exception:
        logger.exception("writing sample %s: Gemini extraction failed", pk)
        messages.error(request, "The clean copy was not made — Gemini did not answer. Try again later.")
        return redirect("usages_edit", pk=sample.usage_id)

    base = sample.image.name.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    if sample.image_clean:
        try: sample.image_clean.delete(save=False)
        except Exception: pass
    sample.image_clean = ContentFile(cleaned, name=f"{base}_clean.jpg")
    sample.save(update_fields=["image_clean"])
    messages.success(request, "Writing sample extracted.")
    return redirect("usages_edit", pk=sample.usage_id)


@login_required
@require_POST
def samples_delete(request, pk):
    sample = get_object_or_404(WritingSample, pk=pk)
    usage_id = sample.usage_id
    for f in (sample.image, sample.image_clean):
        if f:
            try: f.delete(save=False)
            except Exception: pass
    sample.delete()
    undo.say(request, "Writing sample deleted.")
    return redirect("usages_edit", pk=usage_id)


# ----- Pens -----

@login_or_guest_required
def pens_detail(request, pk):
    pen = get_object_or_404(
        Pen.objects.select_related("brand", "rotation"),
        pk=pk,
    )
    photos = list(pen.photos.all())
    usages = list(
        Usage.objects.filter(pen=pen)
        .select_related("ink__brand", "nib")
        .order_by("-begin")
    )
    today = date.today()
    for u in usages:
        u.days = ((u.end or today) - u.begin).days
        u.ink_hex = INK_COLOR_HEX.get(u.ink.color, "#333")
        u.ink_bg = u.ink.swatch_bg
    current = next((u for u in usages if u.end is None), None)
    past = [u for u in usages if u.end is not None]
    total_days = sum(u.days for u in usages)
    distinct_inks = len({u.ink_id for u in usages})

    # Mini gantt bars for this pen
    gantt_bars = []
    year_ticks = []
    if usages:
        earliest = min(u.begin for u in usages)
        latest = today
        start_date = date(earliest.year, 1, 1)
        end_date = date(latest.year, 12, 31)
        total_span = max((end_date - start_date).days, 1)
        for u in sorted(usages, key=lambda x: x.begin):
            b = max(u.begin, start_date)
            e = min(u.end or today, end_date)
            if e < b:
                continue
            left = (b - start_date).days / total_span * 100
            width = max(0.25, (e - b).days / total_span * 100)
            gantt_bars.append({
                "left": left,
                "width": width,
                "hex": u.ink_hex,
                "bg": u.ink_bg,
                "ink": str(u.ink),
                "ink_id": u.ink_id,
                "ink_token": u.ink.share_token,
                "nib": str(u.nib),
                "begin": u.begin,
                "end": u.end,
                "days": u.days,
                "current": u.end is None,
            })
        year_ticks = [
            {"year": y, "left": (date(y, 1, 1) - start_date).days / total_span * 100}
            for y in range(earliest.year, latest.year + 1)
        ]

    pen_samples = list(
        WritingSample.objects.filter(usage__pen=pen)
        .select_related("usage__ink__brand")
        .order_by("-uploaded_at")[:18]
    )

    return render(request, "items/pens/detail.html", {
        "pen": pen,
        "photos": photos,
        "year_bars": inkings.year_bars(usages),
        "current": current,
        "past": past,
        "total_days": total_days,
        "total_usages": len(usages),
        "distinct_inks": distinct_inks,
        "gantt_bars": gantt_bars,
        "year_ticks": year_ticks,
        "samples": pen_samples,
        "public": False,
        "nav": "pens",
    })


@login_or_guest_required
def pens_list(request):
    """The pens, 50 at a time in rotation order (dpypen.items.penindex)."""
    context = penindex.build(request)
    return listing.vary(render(request, penindex.template_for(request, context), context))


@login_required
def pens_create(request):
    form = PenForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        pen = form.save()
        undo.offer(request, f"Added {pen}.", kind="create", model=Pen, pk=pen.pk)
        return redirect("pens_list")
    return render(request, "items/pens/form.html", {
        "form": form,
        "title": "Add pen",
        "submit_label": "Add pen",
        "nav": "pens",
    })


@login_required
def pens_edit(request, pk):
    pen = get_object_or_404(Pen, pk=pk)
    before = undo.snapshot(Pen.objects.get(pk=pk)) if request.method == "POST" else None
    form = PenForm(request.POST or None, instance=pen)
    if request.method == "POST" and form.is_valid():
        form.save()
        undo.offer(request, f"Saved {pen}.", kind="update", frozen=before)
        return redirect("pens_list")
    return render(request, "items/pens/form.html", {
        "form": form,
        "pen": pen,
        "photos": pen.photos.all(),
        "title": f"Edit {pen}",
        "submit_label": "Save",
        "nav": "pens",
    })


@login_required
@require_POST
def pens_delete(request, pk):
    # Photos and inkings cascade with it, files and all — nothing honest to
    # offer as an undo, so this one just says what happened.
    pen = get_object_or_404(Pen, pk=pk)
    label = str(pen)
    pen.delete()
    undo.say(request, f"Deleted {label}.")
    return redirect("pens_list")


@login_required
@require_POST
def pens_photo_add(request, pk):
    pen = get_object_or_404(Pen, pk=pk)
    uploaded = request.FILES.getlist("image")
    made = _save_uploads(request, uploaded, lambda f: PenPhoto.objects.create(pen=pen, image=f))

    # Uploading from the capture queue polishes straight away, so a session of
    # photographing pens does not leave a second pass of "Polish with AI"
    # clicks behind it. A failure here must not lose the photograph.
    if made and request.POST.get("enhance") == "1":
        from dpypen.items.enhance import build_prompt, generate_catalog_shot
        for photo in made:
            try:
                photo.image.open("rb")
                src = photo.image.read()
                photo.image.close()
                styled = generate_catalog_shot(src, prompt=build_prompt(pen),
                                               mime_type="image/jpeg")
                photo.set_styled(styled)
            except Exception:
                # The original is already saved; polish is a nicety, so the
                # upload must still succeed. But swallow it *loudly* — a silent
                # pass here once hid a NameError for every upload in the queue.
                logger.exception("Auto-polish failed for photo %s (pen %s)",
                                 photo.pk, pen.pk)

    nxt = request.POST.get("next")
    if nxt == "queue":
        return redirect("pens_needs_photos")
    return redirect("pens_edit", pk=pk)


@login_required
def pens_needs_photos(request):
    """The pens with no photograph, most-used rotations first.

    Photographing the collection is the one job the app cannot do for itself,
    so it should at least be a single page rather than a hunt: every pen still
    missing a picture, in the order they are actually used, each with its own
    upload."""
    missing = (
        Pen.objects.filter(photos__isnull=True)
        .select_related("brand", "rotation")
        .order_by("rotation__priority", "brand__name", "model")
    )
    groups = {}
    for pen in missing:
        r = pen.rotation
        key = r.priority if r and r.in_use else None
        groups.setdefault(key, []).append(pen)

    ordered = []
    for key in sorted(groups, key=lambda k: (k is None, k)):
        ordered.append({
            "priority": key,
            "label": ("Not in rotation" if key is None else f"Priority {key}"),
            "pens": groups[key],
        })

    done = Pen.objects.filter(photos__isnull=False).distinct().count()
    total = Pen.objects.count()
    return render(request, "items/pens/needs_photos.html", {
        "groups": ordered,
        "done": done,
        "total": total,
        "missing_count": total - done,
        "nav": "pens",
    })


@login_required
@require_POST
def pens_photo_delete(request, pk, photo_pk):
    photo = get_object_or_404(PenPhoto, pk=photo_pk, pen_id=pk)
    for f in (photo.image, photo.thumbnail):
        if f:
            try: f.delete(save=False)
            except Exception: pass
    # The catalogue shot and its twin went with it only on Unstyle: a deleted
    # photo left both on disk (PYPEN-3). Its page-size copy goes at the next
    # deploy (manage.py sized_copies).
    photo.clear_styled(save=False)
    photo.delete()
    undo.say(request, "Photograph deleted.")
    return redirect("pens_edit", pk=pk)


@login_required
@require_POST
def pens_photo_primary(request, pk, photo_pk):
    photo = get_object_or_404(PenPhoto, pk=photo_pk, pen_id=pk)
    min_pos = PenPhoto.objects.filter(pen_id=pk).order_by("position").values_list("position", flat=True).first()
    photo.position = (min_pos - 1) if min_pos is not None else 0
    photo.save(update_fields=["position"])
    return redirect("pens_edit", pk=pk)


@login_required
def pens_photo_edit(request, pk, photo_pk):
    pen = get_object_or_404(Pen.objects.select_related("brand"), pk=pk)
    photo = get_object_or_404(PenPhoto, pk=photo_pk, pen_id=pk)
    from dpypen.items.enhance import build_prompt
    default_prompt = build_prompt(pen)
    return render(request, "items/pens/photo_edit.html", {
        "pen": pen,
        "photo": photo,
        "default_prompt": default_prompt,
        "prompt_value": request.GET.get("prompt", default_prompt),
        "nav": "pens",
    })


@login_required
@require_POST
def pens_photo_enhance(request, pk, photo_pk):
    from django.contrib import messages

    from dpypen.items.enhance import build_prompt, generate_catalog_shot

    pen = get_object_or_404(Pen.objects.select_related("brand"), pk=pk)
    photo = get_object_or_404(PenPhoto, pk=photo_pk, pen_id=pk)
    prompt = request.POST.get("prompt") or build_prompt(pen)

    photo.image.open("rb")
    try:
        src_bytes = photo.image.read()
    finally:
        photo.image.close()
    try:
        styled = generate_catalog_shot(src_bytes, prompt=prompt, mime_type="image/jpeg")
    except Exception:
        logger.exception("pen %s photo %s: Gemini catalog shot failed", pk, photo_pk)
        messages.error(request, "The catalog shot was not made — Gemini did not answer. Try again later.")
        return redirect("pens_photo_edit", pk=pk, photo_pk=photo_pk)

    photo.set_styled(styled)
    messages.success(request, "Catalog shot ready — review side-by-side below.")
    return redirect("pens_photo_edit", pk=pk, photo_pk=photo_pk)


@login_required
@require_POST
def pens_photo_unstyle(request, pk, photo_pk):
    photo = get_object_or_404(PenPhoto, pk=photo_pk, pen_id=pk)
    photo.clear_styled()
    return redirect("pens_photo_edit", pk=pk, photo_pk=photo_pk)


@login_required
@require_POST
def pens_photo_rotate(request, pk, photo_pk):
    import io
    from PIL import Image
    from dpypen.items.models import PHOTO_MAX_SIZE, THUMB_MAX_SIZE, JPEG_QUALITY

    photo = get_object_or_404(PenPhoto, pk=photo_pk, pen_id=pk)
    # Only quarter turns: a stray value was a 500, and any other angle would
    # leave black corners on the photo.
    try:
        degrees = int(request.POST.get("degrees", "90")) % 360
    except ValueError:
        degrees = 90
    if degrees not in (90, 180, 270):
        return redirect("pens_edit", pk=pk)
    for field_name, max_size in (("image", PHOTO_MAX_SIZE), ("thumbnail", THUMB_MAX_SIZE)):
        field = getattr(photo, field_name)
        if not field:
            continue
        field.open("rb")
        try:
            img = Image.open(field)
            img = img.rotate(-degrees, expand=True)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
        finally:
            field.close()
        name = field.name.rsplit("/", 1)[-1]
        field.delete(save=False)
        setattr(photo, field_name, ContentFile(buf.getvalue(), name=name))
    photo.save()
    return redirect("pens_edit", pk=pk)


# ----- Inks -----

@login_or_guest_required
def inks_detail(request, pk):
    ink = get_object_or_404(Ink.objects.select_related("brand", "rotation"), pk=pk)
    today = date.today()
    usages = list(
        Usage.objects.filter(ink=ink)
        .select_related("pen__brand", "ink", "nib")
        .order_by("-begin")
    )
    for u in usages:
        u.days = ((u.end or today) - u.begin).days
    current = [u for u in usages if u.end is None]
    past = [u for u in usages if u.end is not None]
    total_days = sum(u.days for u in usages)
    distinct_pens = len({u.pen_id for u in usages})
    ink_samples = list(
        WritingSample.objects.filter(usage__ink=ink)
        .select_related("usage__pen__brand")
        .order_by("-uploaded_at")[:18]
    )
    swatches = list(InkSwatch.objects.filter(ink=ink).order_by("position", "-uploaded_at")[:12])

    return render(request, "items/inks/detail.html", {
        "ink": ink,
        "year_bars": inkings.year_bars(usages),
        "ink_hex": INK_COLOR_HEX.get(ink.color, "#333"),
        "ink_bg": ink.swatch_bg,
        "current": current,
        "past": past,
        "total_days": total_days,
        "total_usages": len(usages),
        "distinct_pens": distinct_pens,
        "samples": ink_samples,
        "swatches": swatches,
        "public": False,
        "nav": "inks",
    })


@login_or_guest_required
def inks_list(request):
    """The ink cupboard, signed in. Shares every query and every toolbar URL
    with the public one at /pub/inks/ — see dpypen.items.inkindex."""
    context = inkindex.build(request, public=False)
    return listing.vary(render(request, inkindex.template_for(request, context), context))


@login_required
def inks_create(request):
    form = InkForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ink = form.save()
        undo.offer(request, f"Added {ink}.", kind="create", model=Ink, pk=ink.pk)
        return redirect("inks_list")
    return render(request, "items/inks/form.html", {
        "form": form,
        "title": "Add ink",
        "submit_label": "Add ink",
        "nav": "inks",
    })


@login_required
def inks_edit(request, pk):
    ink = get_object_or_404(Ink, pk=pk)
    before = undo.snapshot(Ink.objects.get(pk=pk)) if request.method == "POST" else None
    form = InkForm(request.POST or None, instance=ink)
    if request.method == "POST" and form.is_valid():
        form.save()
        undo.offer(request, f"Saved {ink}.", kind="update", frozen=before)
        return redirect("inks_list")
    return render(request, "items/inks/form.html", {
        "form": form,
        "ink": ink,
        "swatches": list(ink.swatches.all()),
        "title": f"Edit {ink}",
        "submit_label": "Save",
        "nav": "inks",
    })


@login_required
@require_POST
def inks_swatch_add(request, pk):
    ink = get_object_or_404(Ink, pk=pk)
    _save_uploads(request, request.FILES.getlist("image"),
                  lambda f: InkSwatch.objects.create(ink=ink, image=f))
    return redirect("inks_edit", pk=pk)


@login_required
@require_POST
def swatches_extract(request, pk):
    from django.contrib import messages

    from dpypen.items.enhance import generate_ink_swatch

    swatch = get_object_or_404(InkSwatch, pk=pk)
    swatch.image.open("rb")
    try:
        src = swatch.image.read()
    finally:
        swatch.image.close()
    try:
        cleaned = generate_ink_swatch(src, mime_type="image/jpeg")
    except Exception:
        logger.exception("ink swatch %s: Gemini extraction failed", pk)
        messages.error(request, "The clean swatch was not made — Gemini did not answer. Try again later.")
        return redirect("inks_edit", pk=swatch.ink_id)

    base = swatch.image.name.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    if swatch.image_clean:
        try: swatch.image_clean.delete(save=False)
        except Exception: pass
    swatch.image_clean = ContentFile(cleaned, name=f"{base}_clean.jpg")
    swatch.save(update_fields=["image_clean"])
    messages.success(request, "Swatch extracted.")
    return redirect("inks_edit", pk=swatch.ink_id)


@login_required
@require_POST
def swatches_delete(request, pk):
    swatch = get_object_or_404(InkSwatch, pk=pk)
    ink_id = swatch.ink_id
    for f in (swatch.image, swatch.image_clean):
        if f:
            try: f.delete(save=False)
            except Exception: pass
    swatch.delete()
    undo.say(request, "Swatch deleted.")
    return redirect("inks_edit", pk=ink_id)


@login_required
@require_POST
def inks_delete(request, pk):
    ink = get_object_or_404(Ink, pk=pk)
    label = str(ink)
    ink.delete()
    undo.say(request, f"Deleted {label}.")
    return redirect("inks_list")
