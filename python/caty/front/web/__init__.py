#coding:utf-8
import os
import select
import signal
import sys
import threading
from wsgiref.simple_server import make_server
from caty.core.system import System
from caty.front.console import CatyShell
from caty.front.web.console import HTTPConsoleThread
from caty.util import init_writer
from caty.util.syslog import init_log, get_start_log
import caty.core.runtimeobject as ro

def main(args):
    init_log()
    terminator = Terminator()
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP, lambda signum, frame: terminator.restart(signum))
    if hasattr(signal, 'SIGQUIT'):
        signal.signal(signal.SIGQUIT, lambda signum, frame: terminator.exit(signum))
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, lambda signum, frame: terminator.exit(signum))
    if hasattr(signal, 'SIGINT'):
        signal.signal(signal.SIGINT, lambda signum, frame: terminator.exit(signum))
    sl = get_start_log()
    sl.info(ro.i18n.get('Caty server started'))
    while terminator.continue_process == Terminator.CONTINUE:
        try:
            system, is_debug, port, hcon_port = setup(args)
        except Exception, e:
            import traceback
            traceback.print_exc()
            return 1
        if not system:
            return 0
        try:
            server = build_server(system, is_debug, port)
            if hcon_port:
                http_console = HTTPConsoleThread(system, hcon_port)
            else:
                http_console = None
            terminator.set_server(server)
            if http_console:
                http_console.start()
            server.main()
        except select.error, e:
            if e.args[0] == 4:
                pass
            else:
                handle_tb()
                terminator.continue_process = Terminator.FAIL
        except Exception, e:
            handle_tb()
            terminator.continue_process = Terminator.FAIL
    if http_console:
        http_console.httpd.shutdown()
    if terminator.continue_process == Terminator.END:
        sl.info(ro.i18n.get('Caty server ended'))
    else:
        sl.error(ro.i18n.get('Caty server ended'))
    return 0

def unlink_pid():
    if os.path.exists(ro.PID_FILE):
        os.unlink(ro.PID_FILE)

def handle_tb():
    import traceback
    sl = get_start_log()
    sl.error(unicode(traceback.format_exc(), 'utf-8'))
    traceback.print_exc()

def build_server(system, is_debug, port=8000):
    server_module_name = system.server_module_name
    exec 'import %s as server_module' % server_module_name
    server = CatyServerFacade(server_module, system, is_debug, port)
    return server

def check_hcon(option, opt_str, value, parser):
    from optparse import OptionValueError
    if opt_str in ('--hcon-port', '--hcon-name'):
        if parser.values.hcon:
            raise OptionValueError('--hcon-port and --hcon-name is exclusive')
    setattr(parser.values, option.dest, value)

def make_server_opt_parser():
    from caty.front.util import make_base_opt_parser
    parser = make_base_opt_parser('server')
    parser.add_option('-p', '--port', type='int', help=u'サーバーの動作するポート番号')
    parser.add_option('--pid', help=u'サーバーのプロセスIDファイル')
    parser.add_option('--hcon-port', dest='hcon', type='string', action='callback', callback=check_hcon, help=u'hconの動作するポート(uwsgi動作時には無効, hcon-nameと排他)')
    parser.add_option('--hcon-name', dest='hcon', type='string', action='callback', callback=check_hcon, help=u'hconアプリケーション名(uwsgi動作時のみ有効, hcon-portと排他)')
    return parser

def setup(args):
    parser = make_server_opt_parser()
    options, _ = parser.parse_args(args)
    port = 8000
    init_writer(options.system_encoding)
    _help = False
    if os.path.exists(ro.PID_FILE):
        os.unlink(ro.PID_FILE)
    system = System(options.system_encoding, options.debug, options.quiet, options.no_ambient, options.no_app, options.apps or ['root'], options.force_app)
    if options.goodbye:
        print
        print options.goodbye
        return None, None, None, None
    return system, options.debug, options.port, options.hcon

class ConsoleThread(threading.Thread):
    def __init__(self, shell, server):
        threading.Thread.__init__(self)
        self.shell = shell
        self.server = server

    def run(self):
        self.shell.cmdloop()
        self.server.close()

    def stop(self):
        self.shell.do_quit()

class Terminator(object):
    CONTINUE = 0
    END = 1
    FAIL = 2
    def __init__(self):
        self.continue_process = Terminator.CONTINUE

    def set_server(self, server):
        self.closer = threading.Thread(target=lambda :server.close())

    def exit(self, signum):
        from caty.util import cout
        sl = get_start_log()
        cout.writeln('received signal(' + str(signum) + ')')
        sl.info('received signal(' + str(signum) + ')')
        self.continue_process = Terminator.END
        self.closer.start()
        self.closer.join()

    def restart(self, signum):
        from caty.util import cout
        sl = get_start_log()
        sl.info('received signal(' + str(signum) + '), restart')
        cout.writeln('received signal(' + str(signum) + '), restart')
        self.continue_process = Terminator.CONTINUE
        self.closer.start()
        self.closer.join()

class CatyServerFacade(object):
    def __init__(self, server_module, system, is_debug, port):
        self.is_debug = is_debug
        server_class = server_module.get_server(system, is_debug)
        handler_class = server_module.get_handler(system, is_debug)
        dispatcher = server_module.get_dispatcher(system, is_debug)
        self.httpd = make_server('', 
                                 port, 
                                 dispatcher, 
                                 server_class, 
                                 handler_class)
        from caty.util import cout
        cout.writeln("Serving on port %d..." % port)

    def main(self):
        import os
        with open(ro.PID_FILE, 'wb') as f:
            f.write(str(os.getpid()))
        self.httpd.serve_forever()

    def close(self):
        self.httpd.server_close()
        os.unlink(ro.PID_FILE)




