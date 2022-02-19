from django.db import models
import logging

request_logger = logging.getLogger('django.request')


class Dataset(models.Model):
    sid = models.CharField(primary_key=True, max_length=256)
    msg = models.CharField(max_length=1000, null=True)
    rev = models.IntegerField(default=0, null=True)
    gid = models.IntegerField(default=0, null=True)
    reference = models.CharField(max_length=10000, null=True)
    enabled = models.BooleanField(default=False)
    action = models.CharField(max_length=10000, null=True)
    source = models.CharField(max_length=10000)
    created_at = models.CharField(max_length=10)
    updated_at = models.CharField(max_length=10)

    def __str__(self):
        return str(self.sid) + ":" + self.action

    def __init__(self, *args, **kwargs):
        models.Model.__init__(self, *args, **kwargs)