from django.db import models
from djmoney.models.fields import MoneyField

from dpypen.items import constants


class Brand(models.Model):
    name = models.CharField(max_length=30)


class PenRotation(models.Model):
    priority = models.IntegerField()


class Pen(models.Model):
    bought = models.DateField()
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    filling = models.CharField(max_length=30, choices=constants.FILLING)
    klass = models.CharField(max_length=30, choices=constants.CLASSES)
    obtained_from = models.CharField(max_length=30)
    model = models.CharField(max_length=30)
    nationality = models.CharField(max_length=30, choices=constants.NATIONALITIES)
    out = models.BooleanField()
    price = MoneyField(max_digits=5, decimal_places=2, default_currency='PLN')
    price_out = MoneyField(max_digits=5, decimal_places=2, default_currency='PLN')
    rot = models.ForeignKey(PenRotation, on_delete=models.CASCADE)
