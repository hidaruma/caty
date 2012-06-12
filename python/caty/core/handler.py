#coding: utf-8
from caty.util.web import *
from caty.util import error_to_ustr, brutal_encode
from caty.core.facility import COMMIT
from caty.core.i18n import I18nMessageWrapper
from caty.util.path import splitext, dirname, join
from caty.core.command.exception import *
from caty.core.exception import *
from caty.core.schema.base import JsonSchemaError
from caty.util import error_wrapper

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
            proxy = self._verb_dispatcher.get(self._file, path, verb, method)
            if proxy is None:
                _f = self._file.opendir(path + '/')
                if _f.exists:
                    cmd = self._interpreter.build(u'http:found %0', 
                                                  None, 
                                                  [join(self._env['HOST_URL'], self._app_path, path) + '/'], 
                                                  transaction=transaction)
                else:
                    raise IOError(path)
            else:
                if proxy.lock_cmd: # 排他制御
                    cmd = self._interpreter._instantiate(proxy.lock_cmd, opts, [path, path], transaction=transaction)
                    lock_file = cmd(None)
                else:
                    lock_file = None
                if 'deprecated' in proxy.annotations:
                    self._app._system.deprecate_logger.debug('path: %s verb: %s' % (path, verb))
                if proxy.compiled:
                    cmd = self._interpreter._instantiate(proxy.instance, opts, [path, path], transaction=transaction)
                else:
                    cmd = self._interpreter.build(proxy.source, opts, [path, path], transaction=transaction)
        except Exception, e:
            return ExceptionAdaptor(e, traceback.format_exc(), self, error_logger)
        return PipelineAdaptor(cmd, self._interpreter.facilities['schema'], self, error_logger, lock_file)
    
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
    def __init__(self, cmd, schema, handler, error_logger, lock_file=None):
        self.__command = cmd
        self.__result = None
        self.__succeed = False
        self.__schema = schema
        self.i18n = I18nMessageWrapper(handler._app.i18n, handler._env)
        self.env = handler._env
        self.app = handler._app
        self.error_logger = error_logger
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
            result = self.__execute(input, debug)
            self.schema['WebOutput'].validate(result)
            transaction = True
        except PipelineInterruption, e:
            result = e.json_obj
            transaction = True
        except PipelineErrorExit, e:
            result = e.json_obj
            transaction = False
        except SubCatyException, e:
            result = self._dispatch_error(e)
            transaction = False
        except CatyException, e:
            transaction = False
            result = self._make_error_response(e)
        except JsonSchemaError, e:
            transaction = False
            result = {
                'status': 400,
                'body': e.get_message(self.i18n),
                'header': {
                    'content-type': u'text/plain; charset=utf-8'
                }
            }
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

    def __execute(self, input, debug):
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

    def _dispatch_error(self, e):
        if e.tag == 'FileNotFound':
            return {
                'status': 404,
                'header': {
                    'content-type': 'text/plain; charset=utf-8'
                },
                'body': e.get_message(self.i18n)
            }
        elif e.tag == 'UnableToAccess':
            return {
                'status': 403,
                'header': {
                    'content-type': 'text/plain; charset=utf-8'
                },
                'body': e.get_message(self.i18n)
            }
        else:
            return {
                'status': 500,
                'header': {
                    'content-type': 'text/plain; charset=utf-8'
                },
                'body': e.get_message(self.i18n)
            }

    def _make_error_response(self, e):
        tag = e.tag
        value = e.error_obj
        if tag.startswith('HTTP_'):
            status = int(tag.replace('HTTP_', ''))
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
    def __init__(self, error_obj, tb, handler, error_logger):
        self.__error_obj = error_obj
        self.__tb = tb
        PipelineAdaptor.__init__(self, None, None, handler, error_logger)
        self.error_logger = error_logger

    def _handle_pipeline(self, input, debug=False):
        e = self.__error_obj
        if debug:
            print self.__tb
        if isinstance(e, SubCatyException):
            result = self._dispatch_error(e)
        elif isinstance(e, CatyException):
            result = self._make_error_response(e)
        else:
            self.error_logger.write(self.__tb)
            result = {
                'status': 500,
                'body': unicode(self.__tb, 'utf-8') if debug else u'Internal Server Error',
                'header': {
                    'content-type': u'text/plain; charset=utf-8',
                }
            }
        #print self.__tb
        return result, False

class ErrorLogHandler(object):
    def __init__(self, app, path, verb, method):
        self._error_logger = app._system.error_logger
        self._path = path
        self._method = method
        self._verb = verb

    def write(self, msg):
        self._error_logger.error('%s %s%s /%s: %s' % (self.format_date_time(), self._path, self._verb, self._method, self._format(msg)))

    def _format(self, msg):
        return msg.replace('\n', '\\n').replace('\r', '\\r')

    def format_date_time(self):
        now = time.time()
        year, month, day, hh, mm, ss, x, y, z = time.localtime(now)
        s = "%02d/%3s/%04d %02d:%02d:%02d" % (
                day, self.monthname[month], year, hh, mm, ss)
        return s
    monthname = [None,
                 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

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
        method = environ.get('REQUEST_METHOD')
        content_type = environ.get('CONTENT_TYPE', u'')
        if input is None:
            input = environ['wsgi.input']
        else:
            input = StringIO(input)
        cs = self.encoding
        if ';' in content_type:
            content_type, rest = map(str.strip, content_type.split(';', 1))
            if rest.startswith('charset'):
                cs = rest.split('=').pop(1)
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
                cl = 0
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



