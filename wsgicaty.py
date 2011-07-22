import sys
sys.path.insert(0, './python')
sys.path.insert(1, './python/lib/BeautifulSoup')
sys.path.insert(1, './python/lib/antlr')
sys.path.insert(1, './python/lib/topdown')
sys.path.insert(1, './python/lib/simplejson')
sys.path.insert(1, './python/lib/csslib')
sys.path.insert(1, './python/lib/pbc')
sys.path.insert(1, './python/lib/creole')
sys.path.insert(1, './lib/')

import os
from caty.core.system import System
from caty.front.web import setup
from caty.front.console import CatyShell, get_encoding
from caty.util import init_writer
system, is_debug, port, shell = setup([])
server_module_name = system.server_module_name
exec 'import %s as server_module' % server_module_name
    #server_class = server_module.get_server(system, is_debug)
    #handler_class = server_module.get_handler(system, is_debug)
dispatcher = server_module.get_dispatcher(system, is_debug)
application = dispatcher

