# Generated by Django 2.2.27 on 2022-02-19 11:03

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Dataset',
            fields=[
                ('sid', models.CharField(max_length=256, primary_key=True, serialize=False)),
                ('msg', models.CharField(max_length=1000, null=True)),
                ('rev', models.IntegerField(default=0, null=True)),
                ('gid', models.IntegerField(default=0, null=True)),
                ('reference', models.CharField(max_length=10000, null=True)),
                ('enabled', models.BooleanField(default=False)),
                ('action', models.CharField(max_length=10000, null=True)),
                ('source', models.CharField(max_length=10000)),
                ('created_at', models.CharField(max_length=10)),
                ('updated_at', models.CharField(max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name='DatasetProperties',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sid', models.CharField(max_length=256)),
                ('property', models.CharField(max_length=10000)),
                ('value', models.CharField(max_length=10000, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='LocalDatasetChanges',
            fields=[
                ('sid', models.CharField(max_length=256, primary_key=True, serialize=False)),
                ('action', models.CharField(max_length=10000)),
                ('last_mtime', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='MetadataHistogram',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('property', models.CharField(blank=True, db_column='property', max_length=10000, null=True)),
                ('value', models.CharField(blank=True, db_column='value', max_length=10000, null=True)),
                ('number_of_datasets', models.IntegerField(blank=True, db_column='number_of_datasets', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Stats',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.IntegerField(default=0)),
                ('files', models.IntegerField(default=0)),
            ],
        ),
    ]
