# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-03-06 22:17
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('legislation_models', '0010_bill_full_text_link'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sponsor',
            name='legislator',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='legislation_models.Legislator'),
        ),
    ]
