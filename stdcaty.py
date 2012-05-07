#!/usr/bin/python
import sys
sys.path.insert(0, './python')
sys.path.insert(1, './python/lib/topdown')
sys.path.insert(1, './python/lib/csslib')
sys.path.insert(1, './python/lib/pbc')
sys.path.insert(1, './python/lib/creole')
sys.path.insert(1, './lib/')

import caty
if __name__ == '__main__':
    sys.exit(caty.main(sys.argv[1:]))

