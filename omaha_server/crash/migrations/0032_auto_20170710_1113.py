# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2017-07-10 11:13
from __future__ import unicode_literals

from django.db import migrations
from crash.utils import get_channel

def update_channels(apps, schema_editor):
    Crash = apps.get_model("crash", "Crash")
    crashes = Crash.objects.all().exclude(build_number='')
    crashes = crashes.exclude(os='').iterator()
    for obj in crashes:
        obj.channel = get_channel(obj.build_number, obj.os)
        obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ('crash', '0031_crash_channel'),
    ]

    operations = [
        migrations.RunPython(
            update_channels,
            reverse_code=migrations.RunPython.noop
        ),
    ]
