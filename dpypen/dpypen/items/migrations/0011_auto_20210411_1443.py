# Generated by Django 3.1.8 on 2021-04-11 14:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0010_auto_20210411_1438'),
    ]

    operations = [
        migrations.AlterField(
            model_name='penrotation',
            name='priority',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
