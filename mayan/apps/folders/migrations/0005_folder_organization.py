# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import organizations.shortcuts


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0001_initial'),
        ('folders', '0004_documentfolder'),
    ]

    operations = [
        migrations.AddField(
            model_name='folder',
            name='organization',
            field=models.ForeignKey(default=organizations.shortcuts.get_current_organization, to='organizations.Organization'),
            preserve_default=True,
        ),
    ]
