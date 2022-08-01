#!/usr/bin/python3

import sys
sys.path.insert(0, "/usr/local/opnsense/site-python")
import ujson
from lib.datasetcache import DatasetCache
from params import update_params

# Because rule parsing isn't very useful when the rule definitions didn't change we create a single json file
# to hold the last results (combined with creation date and number of files).
if __name__ == '__main__':
    rc = DatasetCache()
    # if rc.is_changed():
    #     rc.create()

    # load parameters, ignore validation here the search method only processes valid input
    parameters = {'limit': '0', 'offset': '0', 'sort_by': '', 'filter': ''}
    update_params(parameters)
    # rename, filter tag to filter_txt
    parameters['filter_txt'] = parameters['filter']
    del parameters['filter']

    # dump output
    result = rc.search(**parameters)
    result['parameters'] = parameters
    print(ujson.dumps(result))
