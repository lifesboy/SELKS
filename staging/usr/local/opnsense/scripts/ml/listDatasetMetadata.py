#!/usr/bin/python3

import ujson
from lib.rulecache import RuleCache

if __name__ == '__main__':
    rc = RuleCache()
    if rc.is_changed():
        rc.create()

    print(ujson.dumps(rc.list_metadata()))
