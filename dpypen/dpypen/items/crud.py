from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from dpypen.items.auth import login_or_guest_required
from dpypen.items.forms import InkForm, PenForm, UsageForm
from dpypen.items.models import Ink, InkSwatch, Pen, PenPhoto, Usage, WritingSample
from dpypen.items.public import INK_COLOR_HEX


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
    form = UsageForm(request.POST or None, instance=usage)
    if request.method == "POST" and form.is_valid():
        form.save()
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
    usage.end = date.today()
    usage.save(update_fields=["end"])
    return redirect("usages_list")


@login_required
@require_POST
def usages_delete(request, pk):
    get_object_or_404(Usage, pk=pk).delete()
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
    from django.core.files.base import ContentFile

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
    def bucket(key, title, subtitle=""):
        if key not in groups:
            groups[key] = {"key": key, "title": title, "subtitle": subtitle, "pens": []}
        return groups[key]

    for p in pens:
        r = p.rotation
        if not r.in_use:
            bucket("defunct", "Defunct / sold")["pens"].append(p)
        elif r.whos == "Tomek" and r.priority in (0, 1, 2, 3):
            bucket(f"p{r.priority}", f"Priority {r.priority}", f"~every {r.how_often} days")["pens"].append(p)
        else:
            bucket("other", "Other active", r.whos)["pens"].append(p)

    ordered = []
    for k in ("p0", "p1", "p2", "p3", "other", "defunct"):
        if k in groups:
            ordered.append(groups[k])

    view = "grid" if request.GET.get("view") == "grid" else "list"

    def _view_url(target_view):
        params = request.GET.copy()
        if target_view == "list":
            params.pop("view", None)
        else:
            params["view"] = target_view
        qs_str = params.urlencode()
        return request.path + (("?" + qs_str) if qs_str else "")

    context = {
        "pens": pens,
        "groups": ordered,
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
        form.save()
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
    form = PenForm(request.POST or None, instance=pen)
    if request.method == "POST" and form.is_valid():
        form.save()
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
    get_object_or_404(Pen, pk=pk).delete()
    return redirect("pens_list")


@login_required
@require_POST
def pens_photo_add(request, pk):
    pen = get_object_or_404(Pen, pk=pk)
    uploaded = request.FILES.getlist("image")
    for f in uploaded:
        PenPhoto.objects.create(pen=pen, image=f)
    return redirect("pens_edit", pk=pk)


@login_required
@require_POST
def pens_photo_delete(request, pk, photo_pk):
    photo = get_object_or_404(PenPhoto, pk=photo_pk, pen_id=pk)
    for f in (photo.image, photo.thumbnail):
        if f:
            try: f.delete(save=False)
            except Exception: pass
    photo.delete()
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
    from django.core.files.base import ContentFile

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
    from django.core.files.base import ContentFile
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
    from django.db.models import Q
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

    inks = list(qs.order_by("used_up", "brand__name", "name"))
    for i in inks:
        i.hex = INK_COLOR_HEX.get(i.color, "#333")
        i.bg = i.swatch_bg

    groups: dict[str, dict] = {}
    for color in INK_COLOR_HEX:
        groups[color] = {"color": color, "hex": INK_COLOR_HEX[color], "inks": []}
    for i in inks:
        if i.color in groups:
            groups[i.color]["inks"].append(i)
    ordered = [g for g in groups.values() if g["inks"]]

    from django.db.models import Count
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

    def _toggle_url(key, new_val):
        params = request.GET.copy()
        if new_val:
            params[key] = new_val
        else:
            params.pop(key, None)
        q = params.urlencode()
        return request.path + (("?" + q) if q else "")

    view = "grid" if request.GET.get("view") == "grid" else "list"

    def _view_url(target_view):
        params = request.GET.copy()
        if target_view == "list":
            params.pop("view", None)
        else:
            params["view"] = target_view
        qs_str = params.urlencode()
        return request.path + (("?" + qs_str) if qs_str else "")

    filters = {
        "include_samples": include_samples,
        "include_used": include_used,
        "color": color_filter,
        "q": q,
        "terms": q.split(),
        "color_chips": color_chips,
        "toggle_samples_url": _toggle_url("samples", "1" if not include_samples else ""),
        "toggle_used_url": _toggle_url("used", "1" if not include_used else ""),
        "view": view,
        "list_url": _view_url("list"),
        "grid_url": _view_url("grid"),
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
        form.save()
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
    form = InkForm(request.POST or None, instance=ink)
    if request.method == "POST" and form.is_valid():
        form.save()
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
    from django.core.files.base import ContentFile

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
    return redirect("inks_edit", pk=ink_id)


@login_required
@require_POST
def inks_delete(request, pk):
    get_object_or_404(Ink, pk=pk).delete()
    return redirect("inks_list")
