from django.db import models
import logging

request_logger = logging.getLogger('django.request')


class Stats(models.Model):
    timestamp = models.DecimalField(max_digits=17, decimal_places=7, default=0.0)
    files = models.IntegerField(default=0)

    def __init__(self, *args, **kwargs):
        models.Model.__init__(self, *args, **kwargs)