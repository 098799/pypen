from datetime import date

from django.db import models
from django.utils.safestring import mark_safe
from djmoney.models.fields import MoneyField

from dpypen.items import constants


class Brand(models.Model):
    def __str__(self):
        return f'{self.name}'

    name = models.CharField(max_length=64, blank=False, null=False, unique=True)
    nationality = models.CharField(max_length=64, choices=constants.NATIONALITIES, blank=False, null=False)


class Rotation(models.Model):
    def __str__(self):
        return mark_safe(
            (f"Rotation <b>{self.priority}</b>, " if self.priority is not None else '')
            + f'{self.whos}, '
            + ("in use" if self.in_use else "defunct")
        )

    priority = models.IntegerField(blank=True, null=True)
    how_often = models.IntegerField(blank=False, null=False)
    whos = models.CharField(max_length=64, blank=False, null=False)
    in_use = models.BooleanField(blank=False, null=False)


class Pen(models.Model):
    def __str__(self):
        return f'{self.brand.name} {self.model}' + (f' {self.finish}' if self.finish else '')

    bought = models.DateField(blank=False, null=False)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, blank=False, null=False)
    model = models.CharField(max_length=64, blank=False, null=False)
    finish = models.CharField(max_length=64, blank=True, null=True)
    filling = models.CharField(max_length=64, choices=constants.FILLING, blank=False, null=False)
    age = models.CharField(max_length=64, choices=constants.CLASSES, blank=False, null=False)
    obtained_from = models.CharField(max_length=64, blank=False, null=False)
    out = models.BooleanField(blank=False, null=False)
    price = MoneyField(max_digits=7, decimal_places=2, default_currency='PLN', blank=False, null=False)
    price_out = MoneyField(max_digits=5, decimal_places=2, default_currency='PLN', blank=True, null=True)
    rotation = models.ForeignKey(Rotation, on_delete=models.CASCADE, blank=False, null=False)


class Nib(models.Model):
    def __str__(self):
        return mark_safe(f'{self.material} <b>{self.width}</b> {self.cut}')

    width = models.CharField(max_length=64, blank=False, null=False)
    cut = models.CharField(max_length=64, choices=constants.NIB_CUTS, blank=False, null=False)
    material = models.CharField(max_length=64, choices=constants.NIB_MATERIALS, blank=False, null=False)


class Ink(models.Model):
    def __str__(self):
        return ("(sample) " if self.volume <= 5 else '') + f'{self.brand.name} ' + (f'{self.line} ' if self.line else '') + f'{self.name}'

    bought = models.DateField(blank=True, null=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, blank=False, null=False)
    line = models.CharField(max_length=64, blank=True, null=True)
    name = models.CharField(max_length=64, blank=False, null=False)
    color = models.CharField(max_length=64, choices=constants.COLORS, blank=False, null=False)
    obtained_from = models.CharField(max_length=64, blank=False, null=False)
    how = models.CharField(max_length=64, choices=constants.HOW, blank=False, null=False)
    price = MoneyField(max_digits=5, decimal_places=2, default_currency='PLN', blank=True, null=True)
    used_up = models.BooleanField(blank=True, null=True)
    used_up_when = models.DateField(blank=True, null=True)
    volume = models.IntegerField(blank=False, null=False)
    rotation = models.ForeignKey(Rotation, on_delete=models.CASCADE, blank=False, null=False)


class Usage(models.Model):
    def __str__(self):
        return mark_safe(f'<b>{self.pen.brand.name} {self.pen.model}</b> inked with <b>{self.ink.brand.name} {self.ink.name}</b> on {self.begin}')

    pen = models.ForeignKey(Pen, on_delete=models.CASCADE, blank=False, null=False)
    nib = models.ForeignKey(Nib, on_delete=models.CASCADE, blank=False, null=False)
    ink = models.ForeignKey(Ink, on_delete=models.CASCADE, blank=False, null=False)
    begin = models.DateField(blank=False, null=False, default=date.today())
    end = models.DateField(blank=True, null=True)
