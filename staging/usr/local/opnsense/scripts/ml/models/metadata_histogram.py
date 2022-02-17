from dbview.models import DbView
import logging

request_logger = logging.getLogger('django.request')


class MetadataHistogram(DbView):

    @classmethod
    def get_view_str(cls):
        return """
            create view metadata_histogram as
                select distinct property, value, count(*) as number_of_datasets
                from  dataset_properties
                where property not in ('created_at', 'updated_at')
                group by property, value
            """