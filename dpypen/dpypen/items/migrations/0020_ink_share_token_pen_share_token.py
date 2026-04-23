import dpypen.items.models
from django.db import migrations, models


def backfill_tokens(apps, schema_editor):
    Pen = apps.get_model("items", "Pen")
    Ink = apps.get_model("items", "Ink")
    from dpypen.items.models import _share_token
    for obj in Pen.objects.filter(share_token=""):
        while True:
            t = _share_token()
            if not Pen.objects.filter(share_token=t).exists():
                obj.share_token = t
                obj.save(update_fields=["share_token"])
                break
    for obj in Ink.objects.filter(share_token=""):
        while True:
            t = _share_token()
            if not Ink.objects.filter(share_token=t).exists():
                obj.share_token = t
                obj.save(update_fields=["share_token"])
                break


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0019_writingsample'),
    ]

    operations = [
        migrations.AddField(
            model_name='ink',
            name='share_token',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
        migrations.AddField(
            model_name='pen',
            name='share_token',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
        migrations.RunPython(backfill_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='ink',
            name='share_token',
            field=models.CharField(blank=True, default=dpypen.items.models._share_token, max_length=32, unique=True),
        ),
        migrations.AlterField(
            model_name='pen',
            name='share_token',
            field=models.CharField(blank=True, default=dpypen.items.models._share_token, max_length=32, unique=True),
        ),
    ]
