# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-02-05 21:43
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('legislation_models', '0007_search_place'),
    ]

    operations = [
        migrations.AddField(
            model_name='search',
            name='notify_on_update',
            field=models.BooleanField(default=False),
        ),
    ]
