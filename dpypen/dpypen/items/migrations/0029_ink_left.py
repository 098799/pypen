from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("items", "0028_usage_verdict"),
    ]

    operations = [
        migrations.AddField(
            model_name="pen",
            name="fill_ml",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="ink",
            name="level_ml",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="ink",
            name="level_on",
            field=models.DateField(blank=True, null=True),
        ),
    ]
