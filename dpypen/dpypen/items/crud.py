import logging
from datetime import date

from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.core.files.base import ContentFile
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from dpypen.items import undo
from dpypen.items.auth import login_or_guest_required
from dpypen.items.forms import InkForm, PenForm, UsageForm
from dpypen.items.models import Ink, InkSwatch, Pen, PenPhoto, Usage, WritingSample
from dpypen.items.public import INK_COLOR_HEX

logger = logging.getLogger(__name__)


# ----- Usages -----

@login_or_guest_required
def usages_list(request):
    from django.core.paginator import Paginator
    today = date.today()
    active = list(
        Usage.objects.filter(end__isnull=True)
        .select_related("pen__brand", "ink__brand", "nib")
        .prefetch_related("pen__photos")
        .order_by("-begin")
    )
    past_qs = (
        Usage.objects.filter(end__isnull=False)
        .select_related("pen__brand", "ink__brand", "nib")
        .order_by("-begin")
    )
    paginator = Paginator(past_qs, 40)
    page_num = request.GET.get("page") or 1
    page = paginator.get_page(page_num)

    for u in active:
        u.days = (today - u.begin).days
        u.ink_hex = INK_COLOR_HEX.get(u.ink.color, "#333")
        u.ink_bg = u.ink.swatch_bg
        photos = list(u.pen.photos.all()[:1])
        if photos:
            p = photos[0]
            u.photo_url = p.image_styled.url if p.image_styled else (p.thumbnail.url if p.thumbnail else p.image.url)
        else:
            u.photo_url = None
    for u in page.object_list:
        u.days = (u.end - u.begin).days
        u.ink_hex = INK_COLOR_HEX.get(u.ink.color, "#333")
        u.ink_bg = u.ink.swatch_bg
    return render(request, "items/usages/list.html", {
        "active": active,
        "past": page.object_list,
        "page": page,
        "paginator": paginator,
        "nav": "usages",
    })


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


@login_required
@require_POST
def usages_sample_add(request, pk):
    usage = get_object_or_404(Usage, pk=pk)
    for f in request.FILES.getlist("image"):
        WritingSample.objects.create(usage=usage, image=f)
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
    except Exception as exc:
        messages.error(request, f"Gemini extraction failed: {exc}")
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
        "current": current,
        "past": past,
        "total_days": total_days,
        "total_usages": len(usages),
        "distinct_inks": distinct_inks,
        "gantt_bars": gantt_bars,
        "year_ticks": year_ticks,
        "samples": pen_samples,
        "nav": "pens",
    })


@login_or_guest_required
def pens_list(request):
    from django.db.models import Q
    q = (request.GET.get("q") or "").strip()
    qs = (
        Pen.objects.select_related("brand", "rotation")
        .prefetch_related("photos")
    )
    for term in q.split():
        qs = qs.filter(
            Q(brand__name__icontains=term) | Q(model__icontains=term)
            | Q(finish__icontains=term) | Q(filling__icontains=term)
        )
    pens = list(qs.order_by("-rotation__in_use", "rotation__priority", "brand__name", "model"))
    for p in pens:
        photos = list(p.photos.all()[:1])
        p.first_photo = photos[0] if photos else None
        if p.first_photo:
            ph = p.first_photo
            p.list_thumb_url = ph.image_styled.url if ph.image_styled else (ph.thumbnail.url if ph.thumbnail else ph.image.url)
            p.list_thumb_styled = bool(ph.image_styled)
        else:
            p.list_thumb_url = None
            p.list_thumb_styled = False

    groups: dict[str, dict] = {}
    # `chip` is the filter-bar label, `title` the section heading. The bar is
    # horizontal and lives on a 390px phone, where "Priority 0" spent ten
    # characters saying what one says.
    def bucket(key, title, subtitle="", chip=None):
        if key not in groups:
            groups[key] = {"key": key, "title": title, "subtitle": subtitle,
                           "chip": chip or title, "pens": []}
        return groups[key]

    for p in pens:
        r = p.rotation
        if not r.in_use:
            bucket("defunct", "Defunct / sold", chip="Defunct")["pens"].append(p)
        elif r.whos == "Tomek" and r.priority in (0, 1, 2, 3):
            bucket(f"p{r.priority}", f"Priority {r.priority}",
                   f"~every {r.how_often} days", chip=str(r.priority))["pens"].append(p)
        else:
            bucket("other", "Other active", r.whos, chip="Other")["pens"].append(p)

    ordered = []
    for k in ("p0", "p1", "p2", "p3", "other", "defunct"):
        if k in groups:
            ordered.append(groups[k])
    groups_ordered_all = list(ordered)

    view = "grid" if request.GET.get("view") == "grid" else "list"

    # Rotation used to be six stacked sections you scrolled past to reach the
    # one you wanted. It reads far better as a filter: pick a priority and the
    # list is only that priority, with the group headings dropped entirely.
    rot = (request.GET.get("rot") or "").strip()
    rot_counts = {g["key"]: len(g["pens"]) for g in ordered}
    if rot and rot in rot_counts:
        ordered = [g for g in ordered if g["key"] == rot]
        for g in ordered:
            g["headless"] = True

    def _url_with(**changes):
        params = request.GET.copy()
        for k, v in changes.items():
            if v is None:
                params.pop(k, None)
            else:
                params[k] = v
        qs_str = params.urlencode()
        return request.path + (("?" + qs_str) if qs_str else "")

    def _view_url(target_view):
        return _url_with(view=None if target_view == "list" else target_view)

    # `rot` is only honoured when it names a real group, so a stale ?rot= from a
    # bookmark falls back to showing everything — "All" has to light up on the
    # same condition the filtering uses, not merely on rot being empty.
    active_rot = rot if rot in rot_counts else ""
    rot_filters = [{
        "key": "",
        "label": "All",
        "title": "All pens",
        "count": len(pens),
        "url": _url_with(rot=None),
        "on": not active_rot,
    }]
    for g in groups_ordered_all:
        rot_filters.append({
            "key": g["key"],
            "label": g["chip"],
            "title": g["title"],
            "count": len(g["pens"]),
            "url": _url_with(rot=g["key"]),
            "on": active_rot == g["key"],
        })

    context = {
        "pens": pens,
        "groups": ordered,
        "rot_filters": rot_filters,
        "rot": rot,
        "query": q,
        "terms": q.split(),
        "nav": "pens",
        "view": view,
        "list_url": _view_url("list"),
        "grid_url": _view_url("grid"),
    }
    partial = request.headers.get("HX-Request") and not request.headers.get("HX-Boosted")
    if partial:
        template = "items/pens/_grid_content.html" if view == "grid" else "items/pens/_list_content.html"
    else:
        template = "items/pens/list.html"
    return render(request, template, context)


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
    made = [PenPhoto.objects.create(pen=pen, image=f) for f in uploaded]

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
                photo.image_styled.save(f"styled-{photo.pk}.jpg",
                                        ContentFile(styled), save=True)
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
    except Exception as exc:
        messages.error(request, f"Gemini catalog shot failed: {exc}")
        return redirect("pens_photo_edit", pk=pk, photo_pk=photo_pk)

    base = photo.image.name.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    if photo.image_styled:
        try: photo.image_styled.delete(save=False)
        except Exception: pass
    photo.image_styled = ContentFile(styled, name=f"{base}_styled.jpg")
    photo.save(update_fields=["image_styled"])
    messages.success(request, "Catalog shot ready — review side-by-side below.")
    return redirect("pens_photo_edit", pk=pk, photo_pk=photo_pk)


@login_required
@require_POST
def pens_photo_unstyle(request, pk, photo_pk):
    photo = get_object_or_404(PenPhoto, pk=photo_pk, pen_id=pk)
    if photo.image_styled:
        try: photo.image_styled.delete(save=False)
        except Exception: pass
    photo.image_styled = None
    photo.save(update_fields=["image_styled"])
    return redirect("pens_photo_edit", pk=pk, photo_pk=photo_pk)


@login_required
@require_POST
def pens_photo_rotate(request, pk, photo_pk):
    import io
    from PIL import Image
    from dpypen.items.models import PHOTO_MAX_SIZE, THUMB_MAX_SIZE, JPEG_QUALITY

    photo = get_object_or_404(PenPhoto, pk=photo_pk, pen_id=pk)
    degrees = int(request.POST.get("degrees", "90"))
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
        .select_related("pen__brand", "nib")
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
        "ink_hex": INK_COLOR_HEX.get(ink.color, "#333"),
        "ink_bg": ink.swatch_bg,
        "current": current,
        "past": past,
        "total_days": total_days,
        "total_usages": len(usages),
        "distinct_pens": distinct_pens,
        "samples": ink_samples,
        "swatches": swatches,
        "nav": "inks",
    })


@login_or_guest_required
def inks_list(request):
    from django.db.models import Count, F, Q
    include_samples = request.GET.get("samples") == "1"
    include_used = request.GET.get("used") == "1"
    color_filter = request.GET.get("color", "")
    q = (request.GET.get("q") or "").strip()

    qs = Ink.objects.select_related("brand", "rotation")
    if not include_samples:
        qs = qs.filter(volume__gt=5)
    if not include_used:
        qs = qs.exclude(used_up=True)
    if color_filter and color_filter in INK_COLOR_HEX:
        qs = qs.filter(color=color_filter)
    for term in q.split():
        qs = qs.filter(
            Q(brand__name__icontains=term) | Q(name__icontains=term)
            | Q(line__icontains=term) | Q(color__icontains=term)
        )

    # "Colour" keeps the grouped-by-hue page that the colour chips navigate.
    # Every other order is a flat list: "newest first", split into sixteen
    # colour sections, is not newest first in any useful sense.
    SORTS = {
        "color":  ("Colour",     ("used_up", "brand__name", "name")),
        "brand":  ("Brand",      ("used_up", "brand__name", "name")),
        "new":    ("Newest",     ("used_up", F("obtained").desc(nulls_last=True), "brand__name")),
        "inked":  ("Most inked", ("used_up", "-n_usages", "brand__name")),
        "volume": ("Volume",     ("used_up", "-volume", "brand__name")),
    }
    sort = request.GET.get("sort") or "color"
    if sort not in SORTS:
        sort = "color"
    inks = list(qs.annotate(n_usages=Count("usage")).order_by(*SORTS[sort][1]))
    for i in inks:
        i.hex = INK_COLOR_HEX.get(i.color, "#333")
        i.bg = i.swatch_bg

    if sort == "color":
        groups: dict[str, dict] = {}
        for color in INK_COLOR_HEX:
            groups[color] = {"color": color, "hex": INK_COLOR_HEX[color], "inks": []}
        for i in inks:
            if i.color in groups:
                groups[i.color]["inks"].append(i)
        ordered = [g for g in groups.values() if g["inks"]]
    else:
        ordered = [{"flat": True, "inks": inks}] if inks else []

    color_counts_qs = Ink.objects
    if not include_samples:
        color_counts_qs = color_counts_qs.filter(volume__gt=5)
    if not include_used:
        color_counts_qs = color_counts_qs.exclude(used_up=True)
    color_counts = dict(
        color_counts_qs.values_list("color").annotate(n=Count("pk"))
    )
    color_chips = [
        {"color": c, "hex": INK_COLOR_HEX[c], "count": color_counts.get(c, 0)}
        for c in INK_COLOR_HEX
        if color_counts.get(c, 0) > 0
    ]

    # These URLs were each spelled out by hand, here and in the templates, and
    # every spelling listed the params it happened to remember — so the colour
    # chips dropped ?q= and the view toggle dropped anything typed since the
    # page rendered. Deriving them from the live query string means a control
    # can only ever set or clear its own key.
    def _url_with(**changes):
        params = request.GET.copy()
        for k, v in changes.items():
            if v:
                params[k] = v
            else:
                params.pop(k, None)
        qs_str = params.urlencode()
        return request.path + (("?" + qs_str) if qs_str else "")

    def _toggle_url(key, new_val):
        return _url_with(**{key: new_val})

    view = "grid" if request.GET.get("view") == "grid" else "list"

    def _view_url(target_view):
        return _url_with(view=None if target_view == "list" else target_view)

    for c in color_chips:
        c["url"] = _url_with(color=None if color_filter == c["color"] else c["color"])

    filters = {
        "include_samples": include_samples,
        "include_used": include_used,
        "color": color_filter,
        "q": q,
        "terms": q.split(),
        "color_chips": color_chips,
        "toggle_samples_url": _toggle_url("samples", "1" if not include_samples else ""),
        "toggle_used_url": _toggle_url("used", "1" if not include_used else ""),
        "clear_url": _url_with(samples=None, used=None, color=None, q=None),
        "view": view,
        "list_url": _view_url("list"),
        "grid_url": _view_url("grid"),
        "sort": sort,
        "sort_label": SORTS[sort][0],
        "sort_options": [
            {"key": k, "label": v[0], "on": k == sort,
             "url": _url_with(sort=None if k == "color" else k)}
            for k, v in SORTS.items()
        ],
    }

    context = {
        "inks": inks,
        "groups": ordered,
        "filters": filters,
        "nav": "inks",
    }
    partial = request.headers.get("HX-Request") and not request.headers.get("HX-Boosted")
    if partial:
        template = "items/inks/_grid.html" if view == "grid" else "items/inks/_content.html"
    else:
        template = "items/inks/list.html"
    return render(request, template, context)


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
    for f in request.FILES.getlist("image"):
        InkSwatch.objects.create(ink=ink, image=f)
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
    except Exception as exc:
        messages.error(request, f"Gemini extraction failed: {exc}")
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
