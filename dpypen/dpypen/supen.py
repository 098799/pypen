import datetime
import math
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dpypen.settings')
django.setup()

import re

import click
import pandas as pd
from tabulate import tabulate
from termcolor import colored

from dpypen.items.models import Ink, Pen, Rotation, Usage


def parse_rotation(rotation):
    if str(rotation).lower() == "ozlem":
        return Rotation.objects.get(whos="Ozlem")

    if str(rotation).lower() == "out":
        return Rotation.objects.get(whos="Tomek", priority=None)

    return Rotation.objects.get(whos="Tomek", priority=rotation)


def colorize(value: int, max_value: int):
    if max_value <= 0:
        color = "grey"
    elif value <= max_value / 2:
        color = "green"
    elif value <= max_value * 3 / 4:
        color = "yellow"
    else:
        color = "red"

    return colored(str(value), color)


def filter_column(column):
    if not column.any():
        return column

    if isinstance(column[0], str):
        return [float(re.findall(r'm(.*?)\x1b', item)[0]) for item in column]

    return column


def interface(rotation, order, item_type):
    def usages(item):
        filter_key = item_type.__name__.lower()
        return Usage.objects.filter(**{filter_key: item})

    def how_many() -> int:
        return len(usages(item))

    def how_long() -> int:
        return sum([((usage.end or datetime.date.today()) - usage.begin).days for usage in usages(item)])

    def when_last() -> int:

        end_dates = usages(item).values_list('end', flat=True)

        if any(not usage for usage in end_dates):
            days_since_last = 0
        elif not end_dates:
            days_since_last = math.inf
        else:
            days_since_last = (datetime.date.today() - sorted(end_dates)[-1]).days

        days_max = item.rotation.how_often

        return colorize(days_since_last, days_max)

    queryset = item_type.objects.all()

    if rotation is not None:
        queryset = queryset.filter(rotation=parse_rotation(rotation))

    if item_type == Ink:
        queryset = queryset.filter(volume__gt=5, used_up=False)

    data = []

    for item in queryset:
        data.append([str(item), how_many(), how_long(), when_last()])

    columns = ['How Many', 'How Long', 'When Last']
    df = pd.DataFrame(data, columns=[item_type.__name__, *columns])

    if order is not None:
        df = df.sort_values(columns[order], key=filter_column)

    print(tabulate(df, headers="keys", tablefmt="psql"))


@click.command()
@click.option('--order', '-o', default=2, type=int)
@click.option('--rotation', '-r', default=None)
def supen(rotation, order):
    if rotation is None:
        interface(rotation=2, order=order, item_type=Pen)
        interface(rotation=1, order=order, item_type=Pen)
        interface(rotation=0, order=order, item_type=Pen)
    else:
        interface(rotation=rotation, order=order, item_type=Pen)


@click.command()
@click.option('--order', '-o', default=2, type=int)
def suink(order):
    interface(rotation=None, order=order, item_type=Ink)
