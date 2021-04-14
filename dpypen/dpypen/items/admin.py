from django.contrib import admin
from django.db.models import F

from dpypen.items import models


@admin.register(models.Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = (
        '__str__',
        'name',
        'nationality',
    )
    ordering = ('name',)


@admin.register(models.PenRotation)
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
    list_display = (
        '__str__',
        'rotation',
        'brand',
        'model',
        'bought',
        'filling',
        'age',
        'obtained_from',
        'price',
        'out',
        'price_out',
    )

    search_fields = (
        'brand',
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
        'used_up',
        'used_up_when',
        'volume',
    )

    search_fields = (
        'brand',
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
        'pen',
        'nib',
        'ink',
    )

    list_filter = (
        'pen',
        'nib',
        'ink',
    )
