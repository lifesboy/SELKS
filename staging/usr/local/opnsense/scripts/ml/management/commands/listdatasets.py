import signal
import sys

sys.path.insert(0, "/usr/local/opnsense/scripts/ml")

from django.core.management.base import BaseCommand
import ujson
import os.path
from lib import metadata, utils
from lib import dataset_source_directory
from lib.datasetcache import DatasetCache


def kill_exists_processing():
    for pid in set(utils.get_process_ids('/scirius/manage.py listdatasets')) - {os.getpid()}:
        os.kill(pid, signal.SIGTERM)


class Command(BaseCommand):
    help = 'List datasets'

    def __init__(self, *args, **kw):
        BaseCommand.__init__(self, *args, **kw)
        self.md = metadata.Metadata()
        self.rc = DatasetCache()

    def add_arguments(self, parser):
        parser.add_argument('--clean-cache', type=int, default=0, help='clean old cache and recreate all')
        parser.add_argument('--parallelism', type=int, default=None, help='parallelism workers to processing')

    def handle(self, *args, **options):
        clean_cache = options['clean_cache'] != 0
        parallelism = options['parallelism']

        if self.rc.is_changed() or clean_cache:
            kill_exists_processing()
            self.rc.create(clean_cache, parallelism)

        # collect all installable rules indexed by (target) filename
        # (filenames should be unique)
        items = dict()
        for rule in self.md.list_rules():
            if not rule['required'] and not rule['deprecated']:
                items[rule['filename']] = rule
                rule_filename = ('%s/%s' % (dataset_source_directory, rule['filename'])).replace('//', '/')
                if os.path.exists(rule_filename):
                    items[rule['filename']]['modified_local'] = os.stat(rule_filename).st_mtime
                else:
                    items[rule['filename']]['modified_local'] = None
        result = {'items': items, 'count': len(items)}
        result['properties'] = self.md.list_rule_properties()

        self.stdout.write(ujson.dumps(ujson.dumps(result)))
