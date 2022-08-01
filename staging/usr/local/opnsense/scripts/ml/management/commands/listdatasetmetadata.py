import sys

sys.path.insert(0, "/usr/local/opnsense/scripts/ml")

from django.core.management.base import BaseCommand, CommandError
import ujson
from lib.datasetcache import DatasetCache


class Command(BaseCommand):
    help = 'List dataset metadata'

    def handle(self, *args, **options):
        rc = DatasetCache()
#         if rc.is_changed():
#             rc.create()

        self.stdout.write(ujson.dumps(rc.list_metadata()))
