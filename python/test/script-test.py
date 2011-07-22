#!/usr/bin/python
# coding: utf-8
import sys
import os
sys.path.insert(0, os.path.abspath('../'))
sys.path.insert(0, os.path.abspath('../lib/antlr/antlr/'))
sys.path.insert(0, os.path.abspath('../lib/BeautifulSoup/'))
sys.path.insert(0, os.path.abspath('../lib/topdown/'))
from caty.testutil.setup import setup_testsite
from caty.util import get_message

def main():
    try:
        e = setup_testsite()
        ip = e.file_interpreter
        c = ip.build('test.caty')
        c(None)
    except Exception, e:
        import traceback
        print unicode(traceback.format_exc(), 'utf-8')
        print get_message(e, 'utf-8')

if __name__ == '__main__':
    main()

