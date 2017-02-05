# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-02-05 12:23
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('legislation_models', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='bill',
            name='status',
            field=models.CharField(choices=[('NU', 'Needs Update'), ('UTD', 'Up-to-date')], default='NU', max_length=3),
        ),
    ]