#coding:utf-8
import os
import select
import signal
import sys
import threading
from wsgiref.simple_server import make_server
from caty.core.system import System
from caty.front.console import CatyShell, get_encoding
from caty.util import init_writer
import caty.core.runtimeobject as ro

def main(args):
    def handle_tb():
        import traceback
        from caty.util import cout, ConsoleWriter
        cw = ConsoleWriter()
        cw.encoding = cout.encoding
        cw.stream = open('failed.log', 'wb')
        cw.write(traceback)

    try:
        try:
            system, is_debug, port, shell = setup(args)
        except:
            return 1
        if not system:
            return 1
        server = build_server(system, is_debug, port)
        closer = threading.Thread(target=lambda: server.close())
        if shell is not None:
            console_thread = ConsoleThread(shell, server)
            console_thread.start()
        signal.signal(signal.SIGHUP, lambda signum, frame: closer.start())
        signal.signal(signal.SIGTERM, lambda signum, frame: closer.start())
        signal.signal(signal.SIGQUIT, lambda signum, frame: closer.start())
        signal.signal(signal.SIGINT, lambda signum, frame: closer.start())
        server.main()
    except select.error, e:
        if e.args[0] == 4:
            pass
        else:
            handle_tb()
    except Exception, e:
        handle_tb()
    return 0

def unlink_pid():
    if os.path.exists(ro.PID_FILE):
        os.unlink(ro.PID_FILE)

def build_server(system, is_debug, port=8000):
    server_module_name = system.server_module_name
    exec 'import %s as server_module' % server_module_name
    server = CatyServerFacade(server_module, system, is_debug, port)
    return server

def setup(args):
    from getopt import getopt
    opts, args = getopt(args, 'cs:dp:h', ['with-console', 'system-encoding=', 'debug', 'port=', 'help', 'pid='])
    debug = False
    system_encoding = None
    use_shell = False
    port = 8000
    _encoding = get_encoding()
    init_writer(_encoding)
    _help = False
    for o, v in opts:
        if o in ('-d', '--debug'):
            debug = True
        elif o in ('-s', '--system-encoding'):
            system_encoding = v
            init_writer(system_encoding)
        elif o in ('-c', '--with-console'):
            use_shell = True
        elif o in ('-p', '--port'):
            port = int(v)
        elif o in ('-h', '--help'):
            _help = True
        elif o == '--pid':
            ro.PID_FILE = v
    if os.path.exists(ro.PID_FILE):
        os.unlink(ro.PID_FILE)
    if _help:
        help()
        return None, None, None, None
    system = System(system_encoding, debug)
    if system._global_config.server_port != port:
        system._global_config.server_port = port
    return system, debug, port, CatyShell(system.get_app('root'), False, debug, system) if use_shell else None

def help():
    from caty.util import OptPrinter
    op = OptPrinter()
    op.add(u'Catyサーバ')
    op.add(u'Usage: python stdcaty.py server [opts]')
    op.add(u'\n起動オプション:')
    op.add(u'-s, --system-encoding', 
u"""コンソール出力時の文字エンコーディング
デフォルト値は環境変数から取得する
取得出来なかった場合はutf-8が使われる""")
    op.add(u'-c, --with-console', u'サーバ起動と同時にコンソールを起動する')
    op.add(u'-p, --port', u'ポート番号を指定する（デフォルト:8000）')
    op.show()
    print 

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
        print "Serving on port %d..." % port

    def main(self):
        import os
        with open(ro.PID_FILE, 'wb') as f:
            f.write(str(os.getpid()))
        self.httpd.serve_forever()

    def close(self):
        self.httpd.server_close()
        try:
            os.unlink(ro.PID_FILE)
        except:
            pass

if __name__ == '__main__':
    sys.exit(main())

