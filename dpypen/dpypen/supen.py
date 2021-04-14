import datetime
import math
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dpypen.settings')
django.setup()

import click
import pandas as pd
from tabulate import tabulate

from dpypen.items import models
from dpypen.items.models import Ink, PenRotation, Usage


def parse_rotation(rotation):
    if rotation.lower() == "ozlem":
        return PenRotation.objects.get(whos="Ozlem")

    if rotation.lower() == "out":
        return PenRotation.objects.get(whos="Tomek", priority=None)

    return PenRotation.objects.get(whos="Tomek", priority=rotation)


@click.command()
@click.option('--order', '-o', default=2, type=int)
@click.option('--rotation', '-r', default=None)
@click.option('--item_type_string', '-i', default="Pen")
def supen(rotation, order, item_type_string):
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
            return 0

        if not end_dates:
            return math.inf

        return (datetime.date.today() - sorted(end_dates)[-1]).days

    item_type = getattr(models, item_type_string.capitalize())
    queryset = item_type.objects.all()

    if rotation is not None:
        queryset = queryset.filter(rotation=parse_rotation(rotation))

    if item_type == Ink:
        queryset = queryset.filter(volume__gt=5, used_up=False)

    data = []

    for item in queryset:
        data.append([str(item), how_many(), how_long(), when_last()])

    columns = ['How Many', 'How Long', 'When Last']
    df = pd.DataFrame(data, columns=[item_type_string.capitalize(), *columns]).sort_values(columns[order])

    if order:
        df = df.sort_values(columns[order])

    print(tabulate(df, headers="keys", tablefmt="psql"))


if __name__ == "__main__":
    supen()
