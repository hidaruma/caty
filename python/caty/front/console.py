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
        self.stream = stream.create(u'uses')
        self.app = site
        self.interpreter = None
        self.wildcat = wildcat
        self.set_prompt()
        self.system = system
        self.last_session = None
        self.server = None
        self.hcon = None
        self.system = system
        self.env = {}
        self.deleted_env = set([])
        self.continue_setenv = None
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
        e = facilities['env'].create(u'updates')
        for k, v in self.env.items():
            e._dict[k] = v
        for k in self.deleted_env:
            if k in e._dict:
                del e._dict[k]
        facilities._facilities['env'] = e.create(u'reads')
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
        else:
            self._echo(u'Unknown option: %s' % line)

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

    def parseline(self, line):
        c, arg, line = cmd.Cmd.parseline(self, line)
        if arg and arg.startswith(':'):
            return None, None, line
        else:
            return c, arg, line


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
    def do_debug(self, line):
        u"""
Usage: debug [on|off]
デバッグモードの切り替え
        """
        mode = line.strip()
        if mode == 'on':
            self.app._system.debug_on()
        elif mode == 'off':
            self.app._system.debug_off()
        else:
            if line.strip():
                self._echo(u'Unknown option: %s' % line)
                return
            self._echo(u'on' if self.env.get('DEBUG', self.app._system.debug) else u'off')
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
        if cmd == 'start':
            if not rest:
                usage()
                return
            if self.hcon is None:
                from caty.util import try_parse
                port = try_parse(int, rest)
                self.hcon = HTTPConsoleThread(self.system, port)
                self.hcon.start()
            else:
                self._echo(u'サーバは既に起動しています')
        elif cmd == 'stop':
            if self.hcon is not None:
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

    def default(self, line):
        if self.continue_setenv:
            return self.do_setenv(line)
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
        from caty.core.casm.cursor import SchemaBuilder
        from caty.core.schema.base import TypeVariable
        scm = command.out_schema
        while isinstance(scm, TypeVariable):
            scm = scm._schema if scm._schema else scm._default_schema
            if not scm:
                return True
        if scm.type == 'void':
            return False
        elif scm.type == 'array':
            sb = SchemaBuilder(None)
            scm = sb._dereference(scm, reduce_option=True)
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
        if self.hcon is not None:
            self.hcon.shutdown()
            self.hcon.stop()
        self.system.finalize()

    def do_setenv(self, line):
        from caty.core.language.util import name_token, CharSeq, option, S, ParseFailed
        from caty.core.script.parser import ScriptParser, NothingTodo
        import string
        if not self.continue_setenv:
            self.continue_setenv = u''
        self.continue_setenv += line
        seq = CharSeq(self.continue_setenv, auto_remove_ws=True)
        force = option(S('--force'))(seq)
        try:
            facilities = self.start_pipeline()
            name = name_token(seq)
            if name[0] in string.ascii_uppercase + '_' and not force:
                self._echo('Invalid env name: %s' % name)
                self.continue_setenv = u''
                return
            seq.parse('{')
            parser = ScriptParser(facilities)
            proxy = parser(seq)
        except NothingTodo:
            self.prompt = '> '
            return
        except ParseFailed as e:
            import traceback
            traceback.print_exc()
            self._echo(u'Syntax error')
            self.continue_setenv = u''
            return
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._echo(u'Some error occuered')
            self.continue_setenv = u''
            return
        try:
            seq.parse('}')
        except:
            self.prompt = '> '
        else:
            if not proxy:
                return
            try:
                proxy.set_module(self.app._schema_module)
                cmd = self.interpreter._instantiate(proxy)
                self.env[name] = cmd(None)
                if name in self.deleted_env:
                    self.deleted_env.remove(name)
                self._echo(u'set: %s => %s' % (pp(self.env[name]), name))
            except:
                import traceback
                traceback.print_exc()
                self._echo(u'Some error occuered')
                self.continue_setenv = u''
            finally:
                self.continue_setenv = None
                self.set_prompt()

    def do_unsetenv(self, line):
        from caty.core.language.util import name_token, CharSeq, option, S, ParseFailed
        from caty.core.script.parser import ScriptParser, NothingTodo
        import string
        seq = CharSeq(line, auto_remove_ws=True)
        force = option(S('--force'))(seq)
        name = name_token(seq)
        if name[0] in string.ascii_uppercase + '_' and not force:
            self._echo('Invalid env name: %s' % name)
            return
        if name in self.env:
            del self.env[name]
        self.deleted_env.add(name)


    @catch
    def do_l(self, line):
        u"""
Usage: load-mods <APP_NAME>
Alias: l
commands, schemata などの再読み込みを行う。
        """
        app_name = line.strip()
        if not app_name:
            app = self.app
        else:
            app = self.app._system.get_app(app_name)
        app.reload()
        self.set_prompt()
        self.interpreter = None
        return False

    @catch
    def do_fl(self, line):
        u"""
Usage: force-load module_name
Alias: fl

on demand宣言されたモジュールを読み込む。
        """
        self.app.force_load(line.strip())
        return False

    @catch
    def do_ia(self, line):
        name = line.strip()
        self.system.init_app(name)

    @catch
    def do_sa(self, line):
        name = line.strip()
        self.system.setup_app(name)

    @catch
    def do_ra(self, line):
        name = line.strip()
        if name == self.app.name or name == 'this':
            self.app.cout.writeln(self.app.i18n.get(u'Current application can not be removed'))
            return
        self.system.remove_app(name)

setattr(CatyShell, 'do_load-mods', CatyShell.do_l)
setattr(CatyShell, 'do_force-load-mod', CatyShell.do_fl)
setattr(CatyShell, 'do_init-app', CatyShell.do_ia)
setattr(CatyShell, 'do_setup-app', CatyShell.do_sa)
setattr(CatyShell, 'do_remove-app', CatyShell.do_ra)

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

def make_console_opt_parser():
    from caty.front.util import make_base_opt_parser
    parser = make_base_opt_parser('console')
    parser.add_option('-e', '--eval', dest='script', help=u'SCRIPTをCatyScriptと解釈して実行し、プロセスを終了する')
    parser.add_option('-f', '--file', dest='files', action='append', help=u'FILEの中身をCatyScriptと解釈して実行し、プロセスを終了する')
    parser.add_option('--dribble', action='store_true', help=u'コンソール操作の履歴をファイルに書き出す。(ファイル名のフォーマット: console.[YYYYmmddHHMMSS].log')
    return parser

def setup_shell(args, cls=CatyShell):
    sitename = []
    wildcat = False
    script = ''
    quiet = False
    debug = False
    parser = make_console_opt_parser()
    options, _ = parser.parse_args(args)
    script = options.script
    init_writer(options.system_encoding)
    system = System(options.system_encoding, options.debug, options.quiet, options.no_ambient, options.no_app, options.apps or ['root'], options.force_app, options.unleash_wildcats)
    if options.goodbye:
        print
        print options.goodbye
        return None, None, None
    site = system.get_app(options.apps[0] if options.apps else 'root')
    shell = cls(site, options.unleash_wildcats, options.debug, system, options.dribble, ' '.join(args))
    return shell, options.files, script


@exc_wrapper
def main(args):
    from caty.util.optionparser import HelpFound
    init_log()
    code = 0
    try:
        import readline
    except:
        readline = None
        print '[WARNING] readline module is not installed.'
    orgdelims = readline.get_completer_delims()
    newdelims = orgdelims.replace('/', '')
    readline.set_completer_delims(newdelims)
    try:
        sh, args, script= setup_shell(args)
    except HelpFound:
        return 0
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

