from django.db import models
import logging

request_logger = logging.getLogger('django.request')


class DatasetProperties(models.Model):
    sid = models.CharField(primary_key=True, max_length=256)
    action = models.CharField(max_length=10000)
    value = models.CharField(max_length=10000)

    def __init__(self, *args, **kwargs):
        models.Model.__init__(self, *args, **kwargs)