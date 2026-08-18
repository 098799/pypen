from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0020_ink_share_token_pen_share_token'),
    ]

    operations = [
        migrations.RenameField(
            model_name='pen',
            old_name='bought',
            new_name='obtained',
        ),
        migrations.RenameField(
            model_name='ink',
            old_name='bought',
            new_name='obtained',
        ),
    ]
