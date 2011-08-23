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
import sys
from caty.core.system import System
from caty.front.web import setup
from caty.front.console import CatyShell, get_encoding
from caty.util import init_writer
from caty.front.web.console import HTTPConsoleApp
import uwsgi
system, is_debug, port, name = setup(sys.argv[1:])
server_module_name = system.server_module_name
exec 'import %s as server_module' % server_module_name
main_app = server_module.get_dispatcher(system, is_debug)
uwsgi.applications = {
    '': main_app,
}
if name:
    if not name.startswith('/'):
        name = '/'+name
    http_console = HTTPConsoleApp(system, is_debug)
    uwsgi.applications[name] = http_console

