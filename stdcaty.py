#!/usr/bin/python
import sys
sys.path.insert(0, './python')
sys.path.insert(1, './python/lib/')
sys.path.insert(1, './lib/')

import caty
if __name__ == '__main__':
    sys.exit(caty.main(sys.argv[1:]))

