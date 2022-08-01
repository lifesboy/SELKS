#!/usr/bin/python3

import ujson
from lib.datasetcache import DatasetCache

if __name__ == '__main__':
    rc = DatasetCache()
    # if rc.is_changed():
    #     rc.create()

    print(ujson.dumps(rc.list_metadata()))
