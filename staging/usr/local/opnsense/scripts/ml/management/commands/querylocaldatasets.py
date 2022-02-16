import sys

sys.path.insert(0, "/usr/local/opnsense/site-python")
sys.path.insert(0, "/usr/local/opnsense/scripts/ml")

from django.core.management.base import BaseCommand
import ujson
from lib.datasetcache import DatasetCache
from params import update_params


class Command(BaseCommand):
    help = 'List datasets'

    def __init__(self, *args, **kw):
        BaseCommand.__init__(self, *args, **kw)
        self.rc = DatasetCache()

    def add_arguments(self, parser):
        parser.add_argument('--limit', action='append', type=int, default=0, help='limit')
        parser.add_argument('--offset', action='append', type=int, default=0, help='offset')
        parser.add_argument('--sort-by', action='append', type=str, default='', help='sort-by')
        parser.add_argument('--filter', action='append', type=str, default='', help='filter')

    def handle(self, *args, **options):
        if self.rc.is_changed():
            self.rc.create()

        # load parameters, ignore validation here the search method only processes valid input
        parameters = dict(
            limit=options['limit'],
            offset=options['offset'],
            sort_by=options['sort_by'],
            filter_txt=options['filter'],
        )

        # dump output
        result = self.rc.search(**parameters)
        result['parameters'] = parameters

        self.stdout.write(ujson.dumps(result))
