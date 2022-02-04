#!/usr/bin/python3

"""
    list training datasets
"""

import os
import os.path
import ujson
from lib import metadata
from lib import dataset_source_directory

md = metadata.Metadata()
if __name__ == '__main__':
    # collect all installable rules indexed by (target) filename
    # (filenames should be unique)
    items = dict()
    for rule in md.list_rules():
        if not rule['required'] and not rule['deprecated']:
            items[rule['filename']] = rule
            rule_filename = ('%s/%s' % (dataset_source_directory, rule['filename'])).replace('//', '/')
            if os.path.exists(rule_filename):
                items[rule['filename']]['modified_local'] = os.stat(rule_filename).st_mtime
            else:
                items[rule['filename']]['modified_local'] = None
    result = {'items': items, 'count': len(items)}
    result['properties'] = md.list_rule_properties()
    print(ujson.dumps(result))
