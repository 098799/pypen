from django.contrib import admin

from dpypen.items import models


admin.site.register(models.Brand)
admin.site.register(models.PenRotation)
admin.site.register(models.Pen)
admin.site.register(models.Nib)
admin.site.register(models.Ink)
admin.site.register(models.Usage)
