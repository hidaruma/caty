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
from caty.front.console import CatyShell
from caty.util import init_writer
from caty.front.web.console import HTTPConsoleApp
import uwsgi

######################################
#### Initialize Caty Core System #####
######################################
system, is_debug, port, name = setup(sys.argv[1:])
server_module_name = system.server_module_name
exec 'import %s as server_module' % server_module_name
main_app = server_module.get_dispatcher(system, is_debug)
uwsgi.applications = {
    '': main_app,
}

######################
#### uWSGI signal ####
######################
SIG_INIT_APP = 98
SLOT_INIT_APP = 1
SIG_REMOVE_APP = 99
SLOT_REMOVE_APP = 2
def init_app_callback(num):
    name = uwsgi.queue_get(SLOT_INIT_APP)
    system.init_app(name)
uwsgi.register_signal(SIG_INIT_APP, 'workers', init_app_callback)


def remove_app_callback(num):
    name = uwsgi.queue_get(SLOT_REMOVE_APP)
    system.remove_app(name)
uwsgi.register_signal(SIG_REMOVE_APP, 'workers', remove_app_callback)

def init_app_sender(name):
    uwsgi.queue_set(SLOT_INIT_APP, name)
    uwsgi.signal(SIG_INIT_APP)
    uwsgi.queue_pop(SLOT_INIT_APP)


def remove_app_sender(name):
    uwsgi.queue_set(SLOT_REMOVE_APP, name)
    uwsgi.signal(SIG_REMOVE_APP)
    uwsgi.queue_pop(SLOT_REMOVE_APP)

if name:
    if not name.startswith('/'):
        name = '/'+name
    http_console = HTTPConsoleApp(system, is_debug)
    http_console.set_init_app_rpc(init_app_sender)
    http_console.set_remove_app_rpc(remove_app_sender)
    uwsgi.applications[name] = http_console

