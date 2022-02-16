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
        parser.add_argument('limit', help='limit')
        parser.add_argument('offset', help='offset')
        parser.add_argument('sort_by', help='sort_by')
        parser.add_argument('filter', help='filter')

    def handle(self, *args, **options):
        limit = options['limit']
        offset = options['offset']
        sort_by = options['sort_by']
        filter = options['filter']

        if self.rc.is_changed():
            self.rc.create()

        # load parameters, ignore validation here the search method only processes valid input
        parameters = {'limit': '0', 'offset': '0', 'sort_by': '', 'filter': ''}
        update_params(parameters)
        # rename, filter tag to filter_txt
        parameters['filter_txt'] = parameters['filter']
        del parameters['filter']

        # dump output
        result = self.rc.search(**parameters)
        result['parameters'] = parameters

        self.stdout.write(ujson.dumps(result))
