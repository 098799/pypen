import json
from datetime import date

from django import forms
from django.db.models import Count, Max

from dpypen.items.models import Ink, Pen, Usage


EMPTY = "— choose —"


def _currency_choices(default: str = "PLN") -> list[tuple[str, str]]:
    """Currencies that actually appear in the DB — keeps the dropdown tight."""
    codes: set[str] = set()
    codes.update(Pen.objects.values_list("price_currency", flat=True).distinct())
    codes.update(Pen.objects
                 .exclude(price_out_currency__isnull=True)
                 .values_list("price_out_currency", flat=True).distinct())
    codes.update(Ink.objects
                 .exclude(price_currency__isnull=True)
                 .values_list("price_currency", flat=True).distinct())
    codes.discard("")
    codes.discard(None)
    if not codes:
        codes.add(default)
    return [(c, c) for c in sorted(codes)]


def _limit_currencies(form: forms.ModelForm, field_name: str):
    if field_name not in form.fields:
        return
    field = form.fields[field_name]
    choices = _currency_choices()
    if hasattr(field, "fields") and len(field.fields) >= 2:
        currency_sub = field.fields[1]
        currency_sub.choices = choices
    widget = getattr(field, "widget", None)
    if widget and hasattr(widget, "widgets") and len(widget.widgets) >= 2:
        widget.widgets[1].choices = choices


class UsageForm(forms.ModelForm):
    class Meta:
        model = Usage
        fields = ["pen", "nib", "ink", "begin", "end"]
        widgets = {
            "begin": forms.DateInput(attrs={"type": "date"}),
            "end": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial.setdefault("begin", date.today())
        self.fields["pen"].queryset = Pen.objects.select_related("brand").order_by(
            "-rotation__in_use", "rotation__priority", "brand__name", "model"
        )
        self.fields["ink"].queryset = Ink.objects.select_related("brand").filter(
            used_up=False, volume__gt=5
        ).order_by("brand__name", "name")
        for name in ("pen", "ink", "nib"):
            self.fields[name].empty_label = EMPTY
            self.fields[name].widget.attrs["class"] = "js-tom-select"
        # Most pens only ever wear one or two of the 30-odd nibs, so the nib
        # list re-sorts itself around the chosen pen: the ones it has worn,
        # most-worn first, above the rest. The shell's Tom Select setup reads
        # these data- attributes; ties go to the nib worn most recently.
        worn: dict[int, list[list[int]]] = {}
        for row in (Usage.objects.values("pen_id", "nib_id")
                    .annotate(n=Count("id"), last=Max("begin"))
                    .order_by("-n", "-last")):
            worn.setdefault(row["pen_id"], []).append([row["nib_id"], row["n"]])
        self.fields["nib"].widget.attrs.update({
            "data-ranked-by": "pen",
            "data-ranks": json.dumps(worn, separators=(",", ":")),
            "data-ranked-label": "Worn by this pen",
            "data-rest-label": "Other nibs",
        })
        self.fields["end"].required = False


class PenForm(forms.ModelForm):
    class Meta:
        model = Pen
        fields = [
            "brand", "model", "finish", "obtained", "filling", "age",
            "obtained_from", "price", "rotation", "out", "price_out",
        ]
        widgets = {
            "obtained": forms.DateInput(attrs={"type": "date"}),
            "age": forms.RadioSelect(attrs={"class": "segmented-input"}),
            "out": forms.CheckboxInput(attrs={"class": "switch-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("brand", "rotation"):
            if name in self.fields:
                self.fields[name].empty_label = EMPTY
        if "age" in self.fields:
            self.fields["age"].choices = [c for c in self.fields["age"].choices if c[0]]
        _limit_currencies(self, "price")
        _limit_currencies(self, "price_out")


class InkForm(forms.ModelForm):
    used_up = forms.BooleanField(
        required=False, label="Used up",
        widget=forms.CheckboxInput(attrs={"class": "switch-input"}),
    )

    class Meta:
        model = Ink
        fields = [
            "brand", "line", "name", "color", "obtained", "obtained_from",
            "how", "price", "volume", "rotation", "used_up", "used_up_when",
            "moi_url",
        ]
        widgets = {
            "obtained": forms.DateInput(attrs={"type": "date"}),
            "used_up_when": forms.DateInput(attrs={"type": "date"}),
            "how": forms.RadioSelect(attrs={"class": "segmented-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("brand", "rotation"):
            if name in self.fields:
                self.fields[name].empty_label = EMPTY
        if "how" in self.fields:
            self.fields["how"].choices = [c for c in self.fields["how"].choices if c[0]]
        if self.instance and self.instance.pk:
            self.fields["used_up"].initial = bool(self.instance.used_up)
        _limit_currencies(self, "price")
