from django.db import models
import logging

request_logger = logging.getLogger('django.request')


class Stats(models.Model):
    timestamp = models.IntegerField(default=0)
    files = models.IntegerField(default=0)

    def __init__(self, *args, **kwargs):
        models.Model.__init__(self, *args, **kwargs)