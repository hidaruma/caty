#coding: utf-8
from caty.util.web import *
from caty.util import error_to_ustr, brutal_encode
from caty.core.facility import COMMIT, ROLLBACK, PEND
from caty.core.i18n import I18nMessageWrapper
from caty.util.path import splitext, dirname, join
from caty.core.command.exception import *
from caty.core.exception import *
from caty.core.schema.base import JsonSchemaError
from caty.util import error_wrapper, brutal_encode

import traceback
import time

class AppDispatcher(object):
    u"""パス名に応じた Caty アプリケーションを返す。
    """
    def __init__(self, system):
        self._system = system

    def dispatch(self, path):
        if path:
            name = path.split('/')[1].strip('/')
        else:
            name = ''
        if name in self._system.app_names and name not in (u'global', u'caty'):
            return self._system.get_app(name)
        else:
            return self._system.get_app('root')

class RequestHandler(object):
    u"""クライアントからのリクエストを編集し、実行可能 Caty コマンドを返す。
    クライアントからのリクエストは以下のように Caty が扱うには問題のあるものが含まれる。

    * ディレクトリ名にスラッシュなし
    * スラッシュの重複

    これらのリクエストを正規な形に修正した上で、 Caty コマンドを生成する。
    この時のクライアントは Web かコンソールかは関係なく、どちらも扱える。
    """

    def __init__(self, interpreter, 
                       env,
                       app):
        self._app_path = env['APP_PATH'].rstrip('/')
        self._config = app.web_config
        self._interpreter = interpreter
        self._verb_dispatcher = app.verb_dispatcher
        self._file = interpreter._facilities['pub'].start().create(u'reads')
        self._encoding = app.encoding
        self._env = env
        env.put('SCRIPT_NAME', app.name if app.name != u'root' else u'')
        self._app = app
        self._verb = ''

    def request(self, path, opts, method, input, transaction=COMMIT):
        _start = time.time()
        cmd = self.make_cmd(path, opts, method, transaction)
        try:
            return cmd(input)
        finally:
            _end = time.time()
            self._app.get_logger('performance').info('%s\t%s\t%s\t%s' % (
                                                    self._env.get('PATH_INFO') if self._env.exists('PATH_INFO') else path, 
                                                    self._verb,
                                                    method,
                                                    str(_end - _start)))
        
    def __del__(self):
        self._file.cancel()


    def make_cmd(self, path, opts, method, transaction=COMMIT):
        path, vpath = self._create_path_and_vpath(path)
        self._env.put('PATH_INFO', vpath)
        # self._env.put('REQUEST_METHOD', method)
        if '_verb' in opts:
            verb = opts['_verb']
            del opts['_verb']
        else:
            verb = ''
        self._verb = verb
        return self._build(path, opts, verb, method, transaction)

    def _create_path_and_vpath(self, src):
        u"""実際にアクセスするファイルのパスとクライアントのアクセスしたパスのペアを返す。
        これは / で終わる URL など、実際に読み込まれるパスがクライアントのアクセスしたパスと異なる時があるためである。
        """
        full_path = unicode(src, self._encoding) if not isinstance(src, unicode) else src
        path = get_virtual_path(self._app_path, full_path)
        vpath = path
        
        return path, vpath
    
    def _build(self, path, opts, verb, method, transaction):
        error_logger = ErrorLogHandler(self._app, path, verb, method)
        try:
            self._verify_access(path, method)
            act = self._verb_dispatcher.get(self._file, path, verb, method)
            if not self._env.get('SECURE') and act.resource_class_entry and act.condition['secure']:
                throw_caty_exception(u'SecurityError', u'$url', url=join(self._env['HOST_URL'], self._app_path, path), path=join(self._app_path, path))
            if not self._env.get('LOGGED') and act.resource_class_entry and act.condition['logged']:
                throw_caty_exception(u'NotLoggedIn', u'$url', url=join(self._env['HOST_URL'], self._app_path, path))
            proxy = act.resource_class_entry
            if proxy is None:
                _f = self._file.opendir(path + '/')
                if _f.exists:
                    cmd = self._interpreter.build(u'webio:found %0', 
                                                  None, 
                                                  [join(self._env['HOST_URL'], self._app_path, path) + '/'], 
                                                  transaction=transaction)
                else:
                    raise IOError(path)
            else:
                if proxy.lock_cmd: # 排他制御
                    cmd = self._interpreter._instantiate(proxy.lock_cmd, opts, [path], transaction=transaction)
                    lock_file = cmd(None)
                else:
                    lock_file = None
                self._env.put(u'ACTION', proxy.canonical_name)
                if 'deprecated' in proxy.annotations:
                    self._app._system.deprecate_logger.debug('path: %s verb: %s' % (path, verb))
                if proxy.compiled:
                    cmd = self._interpreter._instantiate(proxy.instance, opts, [path], transaction=transaction)
                else:
                    cmd = self._interpreter.build(proxy.source, opts, [path, path], transaction=transaction)
        except Exception, e:
            return ExceptionAdaptor(e, self._interpreter, traceback.format_exc(), self, error_logger)
        return PipelineAdaptor(cmd, self._interpreter, self, error_logger, lock_file, transaction)
    
    def _verify_access(self, path, method):
        if path.endswith('/'): return
        fname = path.rsplit('/', 1).pop(-1)
        if fname.startswith('.'):
            raise FileNotFound(path=path)
        if fname.startswith('_') and method.lower() != 'get':
            throw_caty_exception(
                'HTTP_405',
                u'Only GET access is allowed'
                )

class PipelineAdaptor(object):
    u"""コマンドを実行した後で適切なエラーハンドリングを行う。
    """
    def __init__(self, cmd, interpreter, handler, error_logger, lock_file=None, transaction=COMMIT):
        self.__command = cmd
        self.__result = None
        self.__succeed = False
        self.__interpreter = interpreter
        self.__schema = interpreter.facilities['schema'] if interpreter else None
        self.i18n = I18nMessageWrapper(handler._app.i18n, handler._env)
        self.env = handler._env
        self.app = handler._app
        self.error_logger = error_logger
        self.error_dispatcher = ErrorDispacher(self.i18n)
        self.__transaction = transaction
        import hashlib
        import os, tempfile
        if lock_file:
            m = hashlib.md5()
            m.update(lock_file)
            tempdir = tempfile.gettempdir()
            lock_dir = tempdir + os.path.sep + m.hexdigest()
            self.lock_file = lock_dir
        else:
            self.lock_file = None

    @property
    def result(self):
        return self.__result

    @property
    def succeed(self):
        return self.__succeed

    @property
    def schema(self):
        return self.__schema

    def __call__(self, input):
        self.exec_cmd(input, self.app._system.debug)
        return self.__result

    def _handle_pipeline(self, input, debug=False):
        try:
            result = self._execute(input, debug)
            self.schema.get_type('WebOutput').validate(result)
            transaction = True
        except PipelineInterruption, e:
            result = e.json_obj
            transaction = True
        except PipelineErrorExit, e:
            result = e.json_obj
            transaction = False
        except CatySignal as e:
            transaction = False
            if self.schema.has_command_type('map-signal') and not self.scheam.is_runaway_signal(e):
                cmd = self.__interpreter.build(u'map-signal', 
                                              None, 
                                              None, 
                                              transaction=self.__transaction)
                result = cmd(e.raw_data)
            else:
                result = self.error_dispatcher.dispatch_signal(e)
        except CatyException, e:
            transaction = False

            if self.schema.has_command_type('map-exception') and not self.schema.is_runaway_exception(e):
                cmd = self.__interpreter.build(u'map-exception', 
                                              None, 
                                              None, 
                                              transaction=self.__transaction)
                result = cmd(e.raw_data)
            else:
                result = self.error_dispatcher.dispatch_error(e)
        except Exception, e:
            tb = traceback.format_exc()
            transaction = False
            self.error_logger.write(tb)
            result = {
                'status': 500,
                'body': brutal_encode(tb, 'utf-8') if debug else u'Internal Server Error',
                'header': {
                    'content-type': u'text/plain; charset=utf-8',
                }
            }

        return result, transaction

    def _execute(self, input, debug):
        try:
            return self.__command(input)
        except Exception, e:
            if debug:
                import traceback
                import caty.util
                caty.util.debug.writeln(traceback)
                caty.util.debug.writeln(e)
            raise

    def exec_cmd(self, input, debug=False):
        try:
            if self.lock_file:
                self.__lock(self.lock_file)
            result, transaction = self._handle_pipeline(input, debug)
            self.__result = result
            self.__succeed = transaction
        finally:
            if self.lock_file:
                self.__unlock(self.lock_file)

    def __lock(self, lock_dir, recur=5):
        import os, random, time
        while os.path.exists(lock_dir):
            time.sleep(random.randrange(3) / 20.0 + recur / 10.0)
        try:
            os.mkdir(lock_dir)
        except:
            if recur:
                self.__lock(lock_dir, recur-1)
            else:
                raise

    def __unlock(self, lock_dir):
        import os
        if os.path.exists(lock_dir):
            os.rmdir(lock_dir)

class ExceptionAdaptor(PipelineAdaptor):
    def __init__(self, error_obj, interpreter, tb, handler, error_logger):
        self.__error_obj = error_obj
        self.__tb = tb
        PipelineAdaptor.__init__(self, None, interpreter, handler, error_logger)
        self.error_logger = error_logger

    def _execute(self, input, debug=False):
        e = self.__error_obj
        if debug:
            print self.__tb
        raise e

class ErrorLogHandler(object):
    def __init__(self, app, path, verb, method):
        self._error_logger = app._system.error_logger
        self._path = path
        self._method = method
        self._verb = verb

    def write(self, msg):
        self._error_logger.error('%s %s%s /%s: %s' % (self.format_date_time(), self._path, self._verb, self._method, self._format(msg)))

    def _format(self, msg):
        return brutal_encode(msg.replace('\n', '\\n').replace('\r', '\\r'), 'utf-8')

    def format_date_time(self):
        now = time.time()
        year, month, day, hh, mm, ss, x, y, z = time.localtime(now)
        s = "%02d/%3s/%04d %02d:%02d:%02d" % (
                day, self.monthname[month], year, hh, mm, ss)
        return s
    monthname = [None,
                 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

class ErrorDispacher(object):
    def __init__(self, i18n):
        self.i18n = i18n

    def dispatch_error(self, e):
        if e.tag == 'ConversionError' or e.tag == 'InputTypeError':
            return {
                'status': 400,
                'header': {
                    'content-type': u'text/plain; charset=utf-8',
                },
                'body': e.get_message(self.i18n)
            }
        elif e.tag == 'SecurityError' or e.tag == 'NotLoggedIn':
            return {
                'status': 403,
                'header': {
                    'content-type': u'text/plain; charset=utf-8',
                },
                'body': e.get_message(self.i18n)
            }
        elif e.tag == 'FileNotFound':
            return {
                'status': 404,
                'header': {
                    'content-type': u'text/plain; charset=utf-8'
                },
                'body': e.get_message(self.i18n)
            }
        elif e.tag == 'UnableToAccess':
            return {
                'status': 403,
                'header': {
                    'content-type': u'text/plain; charset=utf-8'
                },
                'body': e.get_message(self.i18n)
            }
        elif e.tag == 'VerbUnmatched':
            return {
                'status': 400,
                "header": {
                    'content-type': u'text/plain; charset=utf-8'
                },
                'body': e.get_message(self.i18n)
            }
        else:
            if e.tag.startswith('HTTP_'):
                status = int(e.tag.replace('HTTP_', ''))
            else:
                status = 500
            result = {
                'status': status,
                'body': e.get_message(self.i18n),
                'header': {
                    'content-type': u'text/plain; charset=utf-8',
                }
            }
        return result

    def dispatch_signal(self, e):
        return {
            'status': 500,
            'body': self.i18n.get(u'Uncaught signal: $data', data=e),
            'header': {
                'content-type': u'text/plain; charset=utf-8',
            }
        }

class WebInputParser(object):
    def __init__(self, environ, encoding, input=None):
        self.encoding = encoding
        self.input = self._create_input(environ, input)

    def _create_input(self, environ, input=None):
        u"""クエリの処理。
        """
        import cgi
        import caty.jsontools as json
        from caty.jsontools import stdjson
        from StringIO import StringIO
        from caty.util.web import find_encoding
        method = environ.get('REQUEST_METHOD').upper()
        content_type = environ.get('CONTENT_TYPE', u'')
        if input is None:
            input = environ['wsgi.input']
        else:
            input = StringIO(input)
        cs = self.encoding
        newcs = find_encoding(content_type)
        if newcs:
            cs = newcs
        if method not in ('POST', 'PUT'):
            return None
        if content_type in ('application/www-form-urlencoded', 'application/x-www-form-urlencoded', 'multipart/form-data'):
            _env = dict(environ)
            if 'QUERY_STRING' in _env:
                del _env['QUERY_STRING']
            fs = cgi.FieldStorage(fp=input, environ=_env)
            o = {}
            for k in fs.keys():
                v = fs[k]
                if isinstance(v.value, (list, tuple)):
                    o[k] = self._to_unicode(v.value)
                elif hasattr(v, 'filename') and v.filename:
                    o[k + ".filename"] = [unicode(v.filename)]
                    o[k + ".data"] = [v.file.read()]
                else:
                    o[k] = self._to_unicode([v.value])
            return  json.tagged(u'form', o)
        elif content_type == 'application/json':
            cl = environ['CONTENT_LENGTH']
            if not cl:
                cl = -1 
            src = input.read(int(cl))
            if isinstance(src, str):
                src = unicode(src, cs)
            r = json.tagged(u'json', stdjson.loads(src))
            return r
        else:
            if 'text' in content_type:
                return input.read(int(environ['CONTENT_LENGTH'] or 0))
            else:
                return input.read(int(environ['CONTENT_LENGTH'] or 0))
    

    def read(self):
        return self.input or {}

    def _to_unicode(self, seq):
        return [unicode(v, self.encoding) if not isinstance(v, unicode) else v for v in seq]



