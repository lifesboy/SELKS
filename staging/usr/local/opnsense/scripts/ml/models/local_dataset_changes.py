from django.db import models
import logging

request_logger = logging.getLogger('django.request')


class LocalDatasetChanges(models.Model):
    sid = models.CharField(primary_key=True, max_length=256)
    action = models.CharField(max_length=10000)
    last_mtime = models.FloatField(default=0.0)

    def __init__(self, *args, **kwargs):
        models.Model.__init__(self, *args, **kwargs)