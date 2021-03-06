# Generated by Django 3.1.8 on 2021-04-11 15:02

from django.db import migrations, models
import djmoney.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0011_auto_20210411_1443'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ink',
            name='bought',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='ink',
            name='color',
            field=models.CharField(choices=[('Black', 'Black'), ('Blue', 'Blue'), ('Blue Black', 'Blue Black'), ('Brown', 'Brown'), ('Burgundy', 'Burgundy'), ('Green', 'Green'), ('Grey', 'Grey'), ('Orange', 'Orange'), ('Olive', 'Olive'), ('Pink', 'Pink'), ('Purple', 'Purple'), ('Red', 'Red'), ('Royal Blue', 'Royal Blue'), ('Teal', 'Teal'), ('Turquoise', 'Turquoise'), ('Yellow', 'Yellow')], max_length=64),
        ),
        migrations.AlterField(
            model_name='ink',
            name='price',
            field=djmoney.models.fields.MoneyField(blank=True, decimal_places=2, default_currency='PLN', max_digits=5, null=True),
        ),
    ]
