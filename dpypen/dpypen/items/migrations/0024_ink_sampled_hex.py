from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0023_inkswatch'),
    ]

    operations = [
        migrations.AddField(
            model_name='ink',
            name='sampled_hex',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
