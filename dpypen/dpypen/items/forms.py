import json
from datetime import date

from django import forms
from django.db.models import Count, Max, Q
from django.utils import timezone

from dpypen.items import constants
from dpypen.items.models import Brand, Ink, Pen, Usage


EMPTY = "— choose —"


def _choose(form, name):
    """Django's "---------" says "— choose —" like the other selects (U14)."""
    f = form.fields.get(name)
    if f is not None and getattr(f, "choices", None):
        f.choices = [("", EMPTY) if not v else (v, t) for v, t in f.choices]


def _int(v):
    try:
        return int(getattr(v, "pk", v))
    except (TypeError, ValueError):
        return None


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
        fields = ["pen", "nib", "ink", "begin", "end", "verdict", "note"]
        widgets = {
            "begin": forms.DateInput(attrs={"type": "date"}),
            "end": forms.DateInput(attrs={"type": "date"}),
            "verdict": forms.RadioSelect,
            "note": forms.TextInput(attrs={"placeholder": "Wet, a little dry, shading, cleaned out easily", "maxlength": 200}),
        }
        labels = {"verdict": "How did it write?", "note": "A note"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial.setdefault("begin", date.today())
        self.fields["pen"].queryset = Pen.objects.select_related("brand").order_by(
            "-rotation__in_use", "rotation__priority", "brand__name", "model"
        )
        # The bottles in use and the samples (a vial inks a pen too), plus the
        # ink this inking already has and the one asked for (?ink=), even used
        # up: an old inking of a used-up ink could not be saved, and "Use this
        # ink" on a sample opened an empty field (UX U4).
        keep = {i for i in (self.instance.ink_id, _int(self.initial.get("ink")), _int(self.data.get("ink"))) if i}
        self.fields["ink"].queryset = Ink.objects.select_related("brand").filter(
            Q(used_up=False) | Q(pk__in=keep)
        ).order_by("brand__name", "name")
        self.fields["ink"].label_from_instance = lambda i: str(i) + (" · used up" if i.used_up else "")
        # A pen that is inked says with what, so a second open fill is not made by mistake (U15).
        self._open = {u.pen_id: u for u in Usage.objects.filter(end__isnull=True).select_related("ink__brand")
                      .exclude(pk=self.instance.pk).order_by("begin")}
        self.fields["pen"].label_from_instance = lambda p: str(p) + (
            f" · inked: {self._open[p.pk].ink.brand.name} {self._open[p.pk].ink.name}" if p.pk in self._open else "")
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
        # The old version's form (/prev/) sends neither field; a field a form
        # does not send keeps its value (README "How it wrote").
        self._said = (self.instance.verdict, self.instance.note)

    finish_open = forms.BooleanField(required=False, label="Finish that fill on this inking's day")

    def clean(self):
        data = super().clean()
        begin, end, pen = data.get("begin"), data.get("end"), data.get("pen")
        if begin and end and end < begin:
            self.add_error("end", "Finished before it was inked: check the two dates.")
        old = self._open.get(pen.pk) if pen else None
        # Only a new fill that is still open, and only one that starts after the old one began.
        self.open_fill = None
        if old and not end and begin and begin >= old.begin and not self.instance.pk:
            if data.get("finish_open"):
                self.open_fill = old
            else:
                self.show_finish_open = True
                self.add_error("pen", f"{pen} is inked with {old.ink.brand.name} {old.ink.name} since "
                               f"{old.begin:%-d %b %Y}. Finish that fill first, or tick the box below.")
        return data

    def clean_note(self):
        return " ".join((self.cleaned_data.get("note") or "").split())

    def save(self, commit=True):
        if (self.instance.verdict, self.instance.note) != self._said:
            self.instance.verdict_at = timezone.now()
        usage = super().save(commit=commit)
        if commit and getattr(self, "open_fill", None):
            self.open_fill.end = usage.begin
            self.open_fill.save(update_fields=["end"])
        return usage


class NewBrand(forms.Form):
    """A brand that is not in the list yet, made on save (UX U3: only the admin
    could make one, so a pen or bottle of a new maker could not be added)."""

    new_brand = forms.CharField(required=False, max_length=64, label="New brand")
    new_brand_country = forms.ChoiceField(required=False, label="From", choices=[("", EMPTY), *constants.NATIONALITIES])

    def _brand_init(self):
        self.fields["brand"].required = False

    def _brand_clean(self, data):
        name = (data.get("new_brand") or "").strip()
        if data.get("brand") or "brand" in self.errors or "new_brand_country" in self.errors:
            return
        if not name:
            self.add_error("brand", "Pick a brand, or write a new one below.")
            return
        found = Brand.objects.filter(name__iexact=name).first()
        if not found:
            if not data.get("new_brand_country"):
                self.add_error("new_brand_country", "Where is it from?")
                return
            if self.errors:  # make it only when the rest of the form is fine
                return
            found = Brand.objects.create(name=name, nationality=data["new_brand_country"])
        data["brand"] = found
        self.instance.brand = found


class PenForm(NewBrand, forms.ModelForm):
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
        self._brand_init()
        _choose(self, "filling")
        if not self.instance.pk:
            self.initial.setdefault("obtained", date.today())

    def clean(self):
        data = super().clean()
        self._brand_clean(data)
        return data


class InkForm(NewBrand, forms.ModelForm):
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
        self._brand_init()
        _choose(self, "color")
        if not self.instance.pk:
            self.initial.setdefault("obtained", date.today())
            self.initial.setdefault("how", "Bought")

    def clean(self):
        data = super().clean()
        self._brand_clean(data)
        return data
