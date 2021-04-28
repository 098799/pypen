from django.contrib import admin
from django.utils.safestring import mark_safe

from dpypen.items import models


@admin.register(models.Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = (
        '__str__',
        'name',
        'nationality',
    )
    ordering = ('name',)


@admin.register(models.Rotation)
class RotationAdmin(admin.ModelAdmin):
    list_display = (
        '__str__',
        'priority',
        'how_often',
        'whos',
        'in_use',
    )
    ordering = ('-in_use', 'priority',)


@admin.register(models.Pen)
class PenAdmin(admin.ModelAdmin):
    list_per_page = 200

    list_display = (
        '__str__',
        '_rotation',
        'brand',
        'model',
        'finish',
        'bought',
        'filling',
        # 'age',
        'obtained_from',
        'price',
        # 'out',
        # 'price_out',
    )

    search_fields = (
        'brand__name',
        'model',
        'filling',
    )

    list_filter = (
        'rotation',
        'brand',
        'model',
        'filling',
    )

    ordering = ('-rotation__in_use', 'rotation__priority', 'brand__name', 'model')

    def _rotation(self, pen):
        return mark_safe(f"<b>{pen.rotation.priority}</b>" if pen.rotation.priority is not None else "-")


@admin.register(models.Nib)
class NibAdmin(admin.ModelAdmin):
    list_display = (
        '__str__',
        'width',
        'cut',
        'material',
    )


@admin.register(models.Ink)
class InkAdmin(admin.ModelAdmin):
    list_per_page = 200

    list_display = (
        '__str__',
        'bought',
        'brand',
        'line',
        'name',
        'color',
        'obtained_from',
        'how',
        'price',
        # 'used_up',
        # 'used_up_when',
        'volume',
        # 'rotation',
    )

    search_fields = (
        'brand__name',
        'line',
        'name',
        'color',
        'obtained_from',
        'how',
    )

    list_filter = (
        'brand',
        'line',
        'name',
        'color',
        'obtained_from',
        'how',
    )

    ordering = ('-rotation__in_use', 'brand__name', 'line', 'name')


@admin.register(models.Usage)
class UsageAdmin(admin.ModelAdmin):
    list_display = (
        '__str__',
        'pen',
        'nib',
        'ink',
        'begin',
        'end',
    )

    search_fields = (
        'pen__brand__name',
        'pen__model',
        'nib__width',
        'ink__brand__name',
        'ink__name',
    )

    list_filter = (
        'pen',
        'nib',
        'ink',
    )

    ordering = ('-begin', '-end')
