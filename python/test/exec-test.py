#!/usr/bin/python
# coding: utf-8
import sys
import os
import subprocess
sys.path.insert(0, os.path.abspath('../'))
sys.path.insert(0, os.path.abspath('../lib/antlr/antlr/'))
sys.path.insert(0, os.path.abspath('../lib/BeautifulSoup/'))
sys.path.insert(0, os.path.abspath('../lib/topdown/'))
sys.path.insert(0, os.path.abspath('../lib/csslib/'))
sys.path.insert(0, os.path.abspath('../lib/pbc/'))
sys.path.insert(0, os.path.abspath('../lib/creole/'))
from caty.testutil import TestCase, test
from caty.util import get_message

def load_test(path):
    import imp
    modname = path.replace('/', '.').replace('.py', '').replace('.__init__', '')
    exec 'import %s' % modname
    if modname in sys.modules:
        return sys.modules[modname]
    else:
        return None

def do_test(path):
    t = load_test(path)
    tests = []
    for k, v in t.__dict__.items():
        if type(v) == type and issubclass(v, TestCase) and v != TestCase:
            tests.append(v)
    return test(*tests)

def main():
    error = 0
    for t in filter(lambda x: x.endswith('.py'), sys.argv[1:]):
        try:
            t = t.replace('\\', '/')
            if do_test(t) != 0:
                error = 1
        except:
            import traceback
            traceback.print_exc()
            error = 1
            continue
    return error
if __name__ == '__main__':
    sys.exit(main())

