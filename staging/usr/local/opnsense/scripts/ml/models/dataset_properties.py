from django.db import models
import logging

request_logger = logging.getLogger('django.request')


class DatasetProperties(models.Model):
    sid = models.CharField(max_length=256)
    property = models.CharField(max_length=10000)
    value = models.CharField(max_length=10000, null=True)

    class Meta:
        unique_together = ('sid', 'property',)

    def __init__(self, *args, **kwargs):
        models.Model.__init__(self, *args, **kwargs)