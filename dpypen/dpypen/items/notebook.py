from dataclasses import asdict
from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from dpypen.items.importer import extract_from_image
from dpypen.items.models import Ink, Nib, Pen, Usage


SESSION_KEY = "notebook_extractions"


@login_required
def upload(request):
    if request.method == "POST":
        uploaded = request.FILES.get("image")
        if not uploaded:
            messages.error(request, "Please choose a photo.")
            return redirect("notebook_upload")
        try:
            extractions = extract_from_image(uploaded.read(), media_type=uploaded.content_type or "image/jpeg")
        except Exception as e:
            messages.error(request, f"Claude vision failed: {e}")
            return redirect("notebook_upload")
        request.session[SESSION_KEY] = [asdict(x) for x in extractions]
        return redirect("notebook_review")
    return render(request, "items/notebook/upload.html", {"nav": "import"})


@login_required
@require_http_methods(["GET", "POST"])
def review(request):
    extractions = request.session.get(SESSION_KEY) or []
    if not extractions:
        messages.info(request, "Upload a notebook page first.")
        return redirect("notebook_upload")

    pens = Pen.objects.select_related("brand").order_by("brand__name", "model")
    inks = Ink.objects.select_related("brand").order_by("brand__name", "name")
    nibs = Nib.objects.order_by("material", "width", "cut")

    if request.method == "POST":
        saved = 0
        errors = []
        for idx, row in enumerate(extractions):
            if request.POST.get(f"skip_{idx}") == "on":
                continue
            try:
                pen_id = int(request.POST.get(f"pen_{idx}") or 0)
                ink_id = int(request.POST.get(f"ink_{idx}") or 0)
                nib_id = int(request.POST.get(f"nib_{idx}") or 0)
                begin_str = request.POST.get(f"begin_{idx}") or ""
                end_str = request.POST.get(f"end_{idx}") or ""
                if not (pen_id and ink_id and nib_id and begin_str):
                    errors.append(f"Row {idx + 1}: missing required fields")
                    continue
                Usage.objects.create(
                    pen_id=pen_id,
                    ink_id=ink_id,
                    nib_id=nib_id,
                    begin=datetime.strptime(begin_str, "%Y-%m-%d").date(),
                    end=datetime.strptime(end_str, "%Y-%m-%d").date() if end_str else None,
                )
                saved += 1
            except Exception as e:
                errors.append(f"Row {idx + 1}: {e}")
        del request.session[SESSION_KEY]
        if errors:
            for err in errors:
                messages.warning(request, err)
        messages.success(request, f"Saved {saved} inking{'s' if saved != 1 else ''}.")
        return redirect("usages_list")

    today = date.today().isoformat()
    return render(request, "items/notebook/review.html", {
        "rows": extractions,
        "pens": pens,
        "inks": inks,
        "nibs": nibs,
        "today": today,
        "nav": "import",
    })
