# Generated by Django 3.1.8 on 2021-04-18 14:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0013_ink_rotation'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='PenRotation',
            new_name='Rotation',
        ),
    ]