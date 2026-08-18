from django.contrib import admin
from django.utils.safestring import mark_safe

from dpypen.items import models


@admin.register(models.Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "name",
        "nationality",
    )
    ordering = ("name",)


@admin.register(models.Rotation)
class RotationAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "priority",
        "how_often",
        "whos",
        "in_use",
    )
    ordering = (
        "-in_use",
        "priority",
    )


@admin.register(models.Pen)
class PenAdmin(admin.ModelAdmin):
    list_per_page = 200

    list_display = (
        "__str__",
        "_rotation",
        "brand",
        "model",
        "finish",
        "obtained",
        "filling",
        # 'age',
        "obtained_from",
        "price",
        # 'out',
        # 'price_out',
    )

    search_fields = (
        "brand__name",
        "model",
        "filling",
    )

    list_filter = (
        "rotation",
        "brand",
        "model",
        "filling",
    )

    ordering = ("-rotation__in_use", "rotation__priority", "brand__name", "model")

    def _rotation(self, pen):
        return mark_safe(f"<b>{pen.rotation.priority}</b>" if pen.rotation.priority is not None else "-")


@admin.register(models.Nib)
class NibAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "width",
        "cut",
        "material",
    )


@admin.register(models.Ink)
class InkAdmin(admin.ModelAdmin):
    list_per_page = 200

    list_display = (
        "__str__",
        "obtained",
        "brand",
        "line",
        "name",
        "color",
        "obtained_from",
        "how",
        "price",
        # 'used_up',
        # 'used_up_when',
        "volume",
        # 'rotation',
    )

    search_fields = (
        "brand__name",
        "line",
        "name",
        "color",
        "obtained_from",
        "how",
    )

    list_filter = (
        "brand",
        "line",
        "name",
        "color",
        "obtained_from",
        "how",
    )

    ordering = ("-rotation__in_use", "brand__name", "line", "name")


@admin.register(models.PenPhoto)
class PenPhotoAdmin(admin.ModelAdmin):
    list_display = ("pen", "position", "uploaded_at")
    ordering = ("pen", "position", "-uploaded_at")


@admin.register(models.InviteCode)
class InviteCodeAdmin(admin.ModelAdmin):
    list_display = ("label", "token", "created_at", "expires_at", "revoked_at", "visits", "last_seen_at", "_link")
    readonly_fields = ("token", "created_at", "last_seen_at", "visits", "_link")
    search_fields = ("label", "token")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("label", "expires_at", "revoked_at")}),
        ("Generated", {"fields": ("token", "_link", "visits", "last_seen_at", "created_at")}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.token:
            obj.token = models.InviteCode.generate_token()
        super().save_model(request, obj, form, change)

    def _link(self, obj):
        if not obj.token:
            return "(save first)"
        return mark_safe(
            f'<a href="/i/{obj.token}/" target="_blank">https://pen.grining.eu/i/{obj.token}/</a>'
        )
    _link.short_description = "Invite link"


@admin.register(models.WritingSample)
class WritingSampleAdmin(admin.ModelAdmin):
    list_display = ("usage", "uploaded_at", "has_clean")
    ordering = ("-uploaded_at",)
    def has_clean(self, obj): return bool(obj.image_clean)
    has_clean.boolean = True


@admin.register(models.Usage)
class UsageAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "pen",
        "_nib",
        "ink",
        "begin",
        "end",
    )

    list_editable = (
        "end",
    )

    search_fields = (
        "pen__brand__name",
        "pen__model",
        "nib__width",
        "ink__brand__name",
        "ink__name",
    )

    list_filter = (
        "pen",
        "nib",
        "ink",
    )

    ordering = ("-begin", "-end")

    def _nib(self, usage):
        return str(usage.nib)
