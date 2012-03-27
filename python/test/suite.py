#!/usr/bin/python
# coding: utf-8
import sys
import os
import subprocess

def list_sources():
    for r, d, f in os.walk('../caty'):
        for e in f:
            if e.endswith('.py') and not 'test' in e and not 'test' in r:
                yield os.path.join(r, e)

def find_testcase(path):
    t = path.replace('..', 'unit')
    if os.path.exists(t):
        if os.stat(t).st_size != 0:
            return t
    return None

from optparse import OptionParser
def main():
    o = OptionParser()
    o.add_option('-n', '--no-test', dest='no_test', action='store_false', default=True)
    opt, arg = o.parse_args(None)
    exec_test = opt.no_test
    ran_tests = []
    no_tests = 0
    succ = 0
    fail = []
    num = 0
    for s in list_sources():
        num += 1
        t = find_testcase(s)
        if not t:
            _t = find_testcase(s)
            if not _t:
                print '[!]', s.replace('../', '')
                no_tests += 1
            continue
        print 'testing', t
        ran_tests.append(t)
        if not exec_test:
            continue
        r = subprocess.call(['python', 'exec-test.py', t])
        if r == 0:
            succ += 1
        else:
            fail.append(t)

    _ = 'Unit        :'
    print 'All modules :', num
    print _ , len(ran_tests)
    print 'No tests    :', no_tests
    if not exec_test: return
    print 'Test Result:'
    print '  Succ:', succ
    print '  Fail:', len(fail)
    for f in fail:
        print '   ', f

main()

