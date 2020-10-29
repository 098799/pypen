from django.db import models
from djmoney.models.fields import MoneyField

from dpypen.items import constants


class Brand(models.Model):
    def __str__(self):
        return f'{self.name}'

    name = models.CharField(max_length=30, blank=True, null=True)
    nationality = models.CharField(max_length=30, choices=constants.NATIONALITIES, blank=True, null=True)


class PenRotation(models.Model):
    def __str__(self):
        return f'{self.priority}'

    priority = models.IntegerField(blank=True, null=True)


class Pen(models.Model):
    def __str__(self):
        return f'{self.brand.name} {self.model}'

    bought = models.DateField(blank=True, null=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, blank=True, null=True)
    filling = models.CharField(max_length=30, choices=constants.FILLING, blank=True, null=True)
    klass = models.CharField(max_length=30, choices=constants.CLASSES, blank=True, null=True)
    obtained_from = models.CharField(max_length=30, blank=True, null=True)
    model = models.CharField(max_length=30, blank=True, null=True)
    out = models.BooleanField(blank=True, null=True)
    price = MoneyField(max_digits=5, decimal_places=2, default_currency='PLN', blank=True, null=True)
    price_out = MoneyField(max_digits=5, decimal_places=2, default_currency='PLN', blank=True, null=True)
    rot = models.ForeignKey(PenRotation, on_delete=models.CASCADE, blank=True, null=True)


class Nib(models.Model):
    def __str__(self):
        return f'{self.material} {self.width} {self.cut}'

    width = models.CharField(max_length=30, blank=True, null=True)
    cut = models.CharField(max_length=30, choices=constants.NIB_CUTS, blank=True, null=True)
    material = models.CharField(max_length=30, choices=constants.NIB_MATERIALS, blank=True, null=True)


class Ink(models.Model):
    def __str__(self):
        return f'{self.brand.name} {self.name}'

    bought = models.DateField(blank=True, null=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, blank=True, null=True)
    color = models.CharField(max_length=30, choices=constants.COLORS, blank=True, null=True)
    obtained_from = models.CharField(max_length=30, blank=True, null=True)
    how = models.CharField(max_length=30, choices=constants.HOW, blank=True, null=True)
    name = models.CharField(max_length=30, blank=True, null=True)
    price = MoneyField(max_digits=5, decimal_places=2, default_currency='PLN', blank=True, null=True)
    used_up = models.BooleanField(blank=True, null=True)
    volume = models.IntegerField(blank=True, null=True)


class Usage(models.Model):
    def __str__(self):
        return f'{self.pen.brand.name} {self.pen.model} {self.ink.brand.name} {self.ink.name} {self.begin}'

    pen = models.ForeignKey(Pen, on_delete=models.CASCADE, blank=True, null=True)
    nib = models.ForeignKey(Nib, on_delete=models.CASCADE, blank=True, null=True)
    ink = models.ForeignKey(Ink, on_delete=models.CASCADE, blank=True, null=True)
    begin = models.DateField(blank=True, null=True)
    end = models.DateField(blank=True, null=True)
