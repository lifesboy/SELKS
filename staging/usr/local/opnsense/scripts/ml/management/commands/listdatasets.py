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
    for pid in set(utils.get_process_ids(__file__)) - {os.getpid()}:
        os.kill(pid, signal.SIGTERM)


class Command(BaseCommand):
    help = 'List datasets'

    def __init__(self, *args, **kw):
        BaseCommand.__init__(self, *args, **kw)
        self.md = metadata.Metadata()
        self.rc = DatasetCache()

    def handle(self, *args, **options):
        if self.rc.is_changed():
            kill_exists_processing()
            self.rc.create()

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
