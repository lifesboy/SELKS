from django.db import models
from django.utils import timezone
import logging

request_logger = logging.getLogger('django.request')


class Rule(models.Model):
    sid = models.CharField(primary_key=True, max_length=256)
    msg = models.CharField(max_length=1000)
    rev = models.IntegerField(default=0)
    gid = models.IntegerField(default=0)
    reference = models.CharField(max_length=10000)
    enabled = models.BooleanField(default=False)
    action = models.CharField(max_length=10000)
    source = models.CharField(max_length=10000)
    imported_date = models.DateTimeField(default=timezone.now)
    updated_date = models.DateTimeField(default=timezone.now)
    created = models.DateField(blank=True, null=True)
    updated = models.DateField(blank=True, null=True)

    def __str__(self):
        return str(self.sid) + ":" + self.msg

    def __init__(self, *args, **kwargs):
        models.Model.__init__(self, *args, **kwargs)