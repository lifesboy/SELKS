import logging

from ml.models.dbview.models import DbView
from django.db import models

request_logger = logging.getLogger('django.request')


class MetadataHistogram(DbView):
    property = models.CharField(blank=True, null=True, db_column='property')
    value = models.CharField(blank=True, null=True, db_column='value')
    number_of_datasets = models.IntegerField(blank=True, null=True, db_column='number_of_datasets')

    @classmethod
    def get_view_str(cls):
        return """
            create view metadata_histogram as
                select distinct property, value, count(*) as number_of_datasets
                from  dataset_properties
                where property not in ('created_at', 'updated_at')
                group by property, value
            """
