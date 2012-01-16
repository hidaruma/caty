#coding:utf-8
from getopt import getopt
from caty.core.system import System, StdStream, StreamWrapper
from caty.core.script.builder import CommandCombinator
from caty.core.script.parser import NothingTodo
from caty.jsontools import pp
from caty.core.schema import VoidSchema, ArraySchema
from caty.core.exception import CatyException
from caty.mafs.authorization import AuthoriToken
from caty.session.value import create_variable
from caty.util import get_message, init_writer, cout, debug, error_to_ustr
from caty.util.syslog import init_log
import caty

import cmd, glob, os
import locale
import traceback
import sys
import time
if sys.platform == 'win32':
    from ctypes import windll

def get_encoding():
    try:
        l = locale.getpreferredencoding()
        try:
            ''.decode(l)
            return l
        except Exception, e:
            init_writer('utf-8')
            debug.write(e)
            return 'utf-8'
    except Exception, e:
        init_writer('utf-8')
        debug.write(e)
        return 'utf-8'

def catch(f):
    def _(*args, **kwds):
        try:
            return f(*args, **kwds)
        except Exception, e:
            cout.writeln(traceback)
            cout.writeln(e)
            return None
    _.__doc__ = f.__doc__
    return _

class CatyShell(cmd.Cmd):
    def __init__(self, site, wildcat, debug, system, dribble, cmdline):
        cmd.Cmd.__init__(self)
        self.debug = debug
        self.intro = """Caty interactive shell
        """
        stream = StreamWrapper(StdStream(site.sysencoding))
        self.stream = stream.dual_mode
        self.app = site
        self.interpreter = None
        self.wildcat = wildcat
        self.set_prompt()
        self.system = system
        self.last_session = None
        self.server = None
        self.hcon = None
        self.system = system
        if dribble:
            import time
            self.dribble_file = open(time.strftime('console.%Y%m%d%H%M%S.log'), 'wb')
            self._set_dribble()
            self.dribble_file.write(cmdline)
            self.dribble_file.write(os.linesep)
        else:
            self.dribble_file = None
        import string
        self.type_check = False
        self.identchars = set(list(string.ascii_letters + string.digits + '_-'))

    def start_pipeline(self):
        facilities = self.app.create_facilities(self.last_session)
        if self.interpreter is None:
            self.interpreter = self.app.interpreter.shell_mode(facilities)
        else:
            self.interpreter.update_facility(facilities)
        self.file_loader = self.app.interpreter.file_mode(facilities)
        if not self.wildcat:
            modes = [unicode('console')]
        else:
            modes = [unicode('console'), unicode('test')]
        self.app.init_env(facilities, self.debug, modes, self.system, {'PATH_INFO': u'/'})
        return facilities

    def change_app(self, line):
        if not line.strip():
            name = u'root'
        else:
            name = line.strip()
        if name in self.system.app_names:
            self.app = self.system.get_app(name)
            self.set_prompt()
            self.interpreter = None
        else:
            self._echo(u'%s というアプリケーションは存在しないか、起動しない設定になっています' % line.strip())
        return False

    def do_dribble(self, line):
        l = line.strip()
        if l == 'on':
            if self.dribble_file:
                return
            self.dribble_file = open(time.strftime('console.%Y%m%d%H%M%S.log'), 'wb')
            self._set_dribble()
        elif l == 'off':
            if self.dribble_file:
                self.dribble_file.close()
                self._unset_dribble()
            self.dribble_file = None
        elif not l:
            self._echo('on' if self.dribble_file else 'off')

    def _set_dribble(self):
        cout.streams.append(self.dribble_file)
        debug.streams.append(self.dribble_file)

    def _unset_dribble(self):
        for s in [cout, debug]:
            if self.dribble_file in s.streams:
                s.streams.remove(self.dribble_file)

    def do_help(self, line):
        return self.default('help ' + line)

    def do_type_check(self, line):
        if line.strip() == u'on':
            self.type_check = True
        elif line.strip() == u'off':
            self.type_check = False
        elif line.strip() == u'':
            self._echo('on' if self.type_check else 'off')
        else:
            print u'Usage: type_check [on|off]'

    def onecmd(self, line):
        if self.dribble_file:
            self.dribble_file.write(self.prompt)
            self.dribble_file.write(line)
            self.dribble_file.write(os.linesep)
            self.dribble_file.flush()
        return cmd.Cmd.onecmd(self, line)

    def _echo(self, s):
        cout.writeln(s)
 
    @catch
    def do_quit(self, line):
        u"""
Usage: quite
Caty インタープリタの終了。
        """
        print '\nbye'
        return True

    @catch
    def do_change(self, line):
        u"""
Usage: change <SITE_NAME>
Alias: ch, cd
サイトの変更を行う。
        """
        return self.change_app(line)

    do_ch = do_change
    do_cd = do_change

    @catch
    def do_reload(self, line):
        u"""
Usage: reload
Alias: l
commands, schemata などの再読み込み
        """
        self.app.reload()
        self.set_prompt()
        self.interpreter = None
        return False

    @catch
    def do_debug(self, line):
        u"""
Usage: debug [on|off]
デバッグモードの切り替え
        """
        mode = line.strip()
        if ':' in line:
            return self.default('debug' + line)
        if mode == 'on':
            self.app._system.debug_on()
        elif mode == 'off':
            self.app._system.debug_off()
        else:
            self._echo(u'on' if self.app._system.debug else u'off')
        self.set_prompt()
        return False

    def _format_doc(self, doc):
        lines = doc.strip('\n').split('\n')
        space = 0
        for i in list(lines[0]):
            if i == ' ':
                space += 1
            else:
                break
        d = []
        for l in lines:
            d.append(l.replace(' '*space, '', 1))
        return '\n'.join(d)

    @catch
    def do_server(self, line):
        u"""
Usage: server start|stop
Web サーバの起動・停止を行う
        """
        def usage():
            self._echo(u'使い方: server start [port] または server stop')
        from caty.front.web import build_server
        cmd = line.strip()
        if ' ' in cmd:
            cmd, rest = map(str.strip, line.split(' ', 1))
        else:
            rest = ''
        port = self.app._global_config.server_port
        if cmd == 'start':
            if self.server is None:
                if rest:
                    from caty.util import try_parse
                    port = try_parse(int, rest) or self.app._global_config.server_port
                if self.app._global_config.server_port != port:
                    self.app._global_config.server_port = port
                self.server = ServerThread(build_server(self.system, self.debug, port), port)
                self.server.start()
                if sys.platform == 'win32':
                    windll.kernel32.SetConsoleTitleW(u'Caty Console (%d)' % port)
            else:
                self._echo(u'サーバは既に起動しています')
        elif cmd == 'stop':
            if self.server is not None:
                self.server.shutdown()
                self.server.stop()
                self.server = None
                if sys.platform == 'win32':
                    windll.kernel32.SetConsoleTitleW(u'Caty Console')
                self.app._global_config._configure_server()
            else:
                self._echo(u'サーバが起動していません')
        elif cmd == 'status' or cmd == '':
            if self.server is not None:
                self._echo(self.server.status())
            else:
                self._echo(u'stopped')
        else:
            self._echo(u'未知の引数: %s' % cmd)
            usage()

    @catch
    def do_hcon(self, line):
        u"""
Usage: server start|stop
Web サーバの起動・停止を行う
        """
        def usage():
            self._echo(u'使い方: hcon start port または hcon stop')
        from caty.front.web.console import HTTPConsoleThread
        cmd = line.strip()
        if ' ' in cmd:
            cmd, rest = map(str.strip, line.split(' ', 1))
        else:
            rest = ''
            usage()
            return
        if cmd == 'start':
            if self.server is None:
                from caty.util import try_parse
                port = try_parse(int, rest) or self.app._global_config.server_port
                self.hcon = HTTPConsoleThread(self.system, port)
                self.hcon.start()
            else:
                self._echo(u'サーバは既に起動しています')
        elif cmd == 'stop':
            if self.server is not None:
                self.hcon.shutdown()
                self.hcon.stop()
                self.hcon = None
            else:
                self._echo(u'サーバが起動していません')
        elif cmd == 'status' or cmd == '':
            if self.hcon is not None:
                self._echo(self.hcon.status())
            else:
                self._echo(u'stopped')
        else:
            self._echo(u'未知の引数: %s' % cmd)
            usage()
    do_l = do_reload

    def default(self, line):
        if line == 'EOF':
            print 'bye'
            return True
        if line in ('\n', '\r', '\r\n') and self.prompt.startswith('caty'):
            # 単なる空行には何もしない
            return False
        facilities = self.start_pipeline()
        try:
            # 一連のパイプラインが入力しきっていない場合、 None が返る
            try:
                c = self.interpreter.build(unicode(line.strip(), self.app.sysencoding), type_check=self.type_check)
            except NothingTodo:
                self.set_prompt()
                return False
            if c:
                r = c(None)
                if self.not_void_out(c):
                    o = pp(r)
                    self._echo(o)
                self.set_prompt()
                self.interpreter = None
            else:
                self.prompt = '> '
        except CatyException, e:
            self._echo(traceback)
            m = e.get_message(self.app.i18n)
            self._echo(m)
            self.set_prompt()
            self.interpreter = None
        except Exception, e:
            self._echo(traceback)
            self._echo(e)
            self.set_prompt()
            self.interpreter = None
        finally:
            s = facilities['session'].clone()
            self.last_session = lambda: s
            facilities._facilities.clear()

    def set_prompt(self):
        self.prompt = 'caty:%s> ' % ("" if self.app.name == "_ROOT" else self.app.name)

    def format(self, obj):
        if isinstance(obj, unicode):
            o = '"%s"' % obj
        elif isinstance(obj, dict):
            o = pp(obj)
        elif isinstance(obj, list):
            o = '[%s]' % ', '.join([self.format(v) for v in obj])
        else:
            o = str(obj)
        return o

    def not_void_out(self, command):
        scm = command.out_schema
        if scm.type == 'void':
            return False
        elif scm.type == 'array':
            if all(map(lambda s: s.type == 'void', scm.schema_list)):
                return False
        return True

    def completedefault(self, text, line, bi, ei):
        files = glob.glob(text + '*')
        return list(files)

    def emptyline(self):
        return self.default('\n')

    def exec_files(self, files):
        for f in files:
            self.start_pipeline()
            s = unicode(open(f, 'rb').read(), self.app.encoding)
            try:
                c = self.file_loader.build(s)
                r = c(None)
                if self.not_void_out(c):
                    o = pp(r)
                    self.stream.write(o + '\n')
            except Exception, e:
                cout.writeln(traceback)
                cout.writeln(e)
                print e
                return -1
        return 0

    def exec_script(self, script):
        self.start_pipeline()
        try:
            c = self.file_loader.build(script)
            r = c(None)
            if self.not_void_out(c):
                o = pp(r)
                self.stream.write(o + '\n')
            return 0
        except Exception, e:
            cout.writeln(traceback)
            cout.writeln(e)
            print e
            return -1


    def cmdloop(self, *args, **kwds):
        try:
            cmd.Cmd.cmdloop(self, *args, **kwds)
        except KeyboardInterrupt, e:
            self.cleanup()
            raise

    def cleanup(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.stop()

import threading
class ServerThread(threading.Thread):
    def __init__(self, server, port):
        threading.Thread.__init__(self)
        self.server = server
        self.port = port

    def run(self):
        self.server.main()

    def shutdown(self):
        self.server.httpd.shutdown()

    def stop(self):
        self.server.close()

    def status(self):
        return u'running on port %d' % self.port

import sys
try:
    import simplejson as json
except ImportError:
    import json
def exc_wrapper(f):
    def wrapped(*args, **kwds):
        try:
            return f(*args, **kwds)
        except Exception, e:
            cout.writeln(traceback)
            cout.writeln(error_to_ustr(e))
            return -1
    return wrapped

_encoding = get_encoding()
from caty.util import OptPrinter
def setup_shell(args, cls=CatyShell):
    opts, args = getopt(args, 
                        'e:s:dua:qhf:', 
                        ['eval=', 
                         'system-encoding=', 
                         'app=', 
                         'unleash-wildcats', 
                         'debug', 
                         'quiet', 
                         'help', 
                         'dribble',
                         'file=',
                         'no-ambient',
                         'no-app'])
    sitename = 'root'
    wildcat = False
    system_encoding = locale.getpreferredencoding()
    script = ''
    quiet = False
    global _encoding
    debug = False
    _encoding = get_encoding()
    init_writer(_encoding)
    _help = False
    files = []
    no_ambient = False
    no_app = False
    dribble = False
    for o, v in opts:
        if o in ('-a', '--app'):
            sitename = v
        elif o in ('-u', '--unleash-wildcats'):
            wildcat = True
        elif o in ('-d', '--debug'):
            debug = True
        elif o in ('-s', '--system-encoding'):
            system_encoding = v
            _encoding = v
            init_writer(_encoding)
        elif o in ('-e', '--eval'):
            script = v
        elif o in ('-q', '--quiet'):
            quiet = True
        elif o in ('-h', '--help'):
            _help = True
        elif o in ('-f', '--file'):
            files = [v]
        elif o == '--no-ambient':
            no_ambient = True
        elif o == '--no-app':
            no_app = True
        elif o == '--dribble':
            dribble = True
    if args:
        help(u'不明な引数です: %s' % ', '.join(args))
        return None, None, None
    if _help:
        help()
        return None, None, None
    system = System(_encoding, debug, quiet, no_ambient, no_app, sitename)
    site = system.get_app(sitename)
    shell = cls(site, wildcat, debug, system, dribble, ' '.join(args))
    return shell, files, script

def help(msg=None):
    op = OptPrinter()
    if msg:
        op.add(msg)
    op.add(u'Catyコンソール')
    op.add(u'Usage: python stdcaty.py console [opts]')
    op.add(u'\n起動オプション:')
    op.add(u'-a, --app APP_NAME', u'起動時にAPP_NAMEに移動')
    op.add(u'-s, --system-encoding', 
u"""コンソール出力時の文字エンコーディング
デフォルト値は環境変数から取得する
取得出来なかった場合はutf-8が使われる""")
    op.add(u'-e, --eval SCRIPT', u'起動時にSCRIPTをCatyスクリプトだとして実行する')
    op.add(u'-f, --file SCRIPT_FILE', u'起動時にSCRIPT_FILEを読み込み実行する')
    op.add(u'-q, --quiet', u'起動メッセージを省略')
    op.show()

@exc_wrapper
def main(args):
    global _encoding
    init_log()
    _encoding = get_encoding()
    code = 0
    if sys.platform == 'win32':
        import pyreadline as readline
#        from ctypes import windll
    else:
        import readline
    orgdelims = readline.get_completer_delims()
    newdelims = orgdelims.replace('/', '')
    readline.set_completer_delims(newdelims)
    try:
        sh, args, script= setup_shell(args)
    except:
        import traceback
        traceback.print_exc()
        return 1
    if not sh:
        return 0
    if not args and not script:
        if sys.platform == 'win32':
            windll.kernel32.SetConsoleTitleW(u'Caty Console')
        sh.cmdloop()
        code = 0
    else:
        if not script:
            code = sh.exec_files(args)
        else:
            code = sh.exec_script(script)
    sh.cleanup()
    return code

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

