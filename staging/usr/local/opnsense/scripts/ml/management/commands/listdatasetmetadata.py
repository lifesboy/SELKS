from django.core.management.base import BaseCommand, CommandError
import ujson
from ml.lib.datasetcache import DatasetCache


class Command(BaseCommand):
    help = 'List dataset metadata'

    def handle(self, *args, **options):
        rc = DatasetCache()
        if rc.is_changed():
            rc.create()

        self.stdout.write(ujson.dumps(rc.list_metadata()))
