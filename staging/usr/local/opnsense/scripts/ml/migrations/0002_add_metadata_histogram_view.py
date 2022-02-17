# Generated manually on 2022-02-17 22:19

from django.db import migrations, models
from dbview.helpers import CreateView


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('ml', '0001_initial'),
    ]

    operations = [
        CreateView(
            name='MetadataHistogram',
            fields=[
                ('property', models.CharField(blank=True, null=True)),
                ('value', models.CharField(blank=True, null=True)),
                ('number_of_datasets', models.IntegerField(default=0)),
            ],
        ),
    ]
