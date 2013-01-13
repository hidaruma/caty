# coding: utf-8
from caty.core.command import Builtin
from caty.core.exception import *
import caty.jsontools as json
import caty.jsontools.xjson as xjson
import caty.jsontools.stdjson as stdjson
from caty.util.collection import conditional_dict
from StringIO import StringIO
from caty.util.web import find_encoding

class MakeEnv(Builtin):
    def setup(self, opts, path, query=u''):
        self.__fullpath = opts['fullpath']
        self.__method = opts['method'].upper()
        self.__verb = opts['verb']
        self.__content_type = opts['content-type']
        self.__multiprocess = opts['multiprocess']
        self.__multithread = opts['multithread']
        self.__server_name = opts['server-name']
        self.__server_port = opts['server-port']
        self.__url_scheme = opts['url-scheme']
        self.__query = query
        self.__path = path

    def execute(self, input):
        self._validate_input(input)
        self._fill_default_value()
        if not self.__content_type:
            self.__content_type = u'text/plain' if isinstance(input, unicode) else u'application/octet-stream'
        chunk = self.__path.strip(u'/').split(u'/')
        system = self.current_app._system
        script_name = self.current_app.name
        path = self.__path
        istream = StringIO()
        if self.__fullpath:
            top = chunk.pop(0)
            if top in system.app_names and top not in (u'caty', u'global'):
                script_name = top
                path = u'/' + u'/'.join(chunk)
            else:
                path = self.__path
                script_name = u''
        elif script_name == u'root':
            script_name = u''
        if isinstance(input, unicode):
            input = input.encode(find_encoding(self.__content_type) or self.current_app.encoding)
        length = u''
        if input:
            length = unicode(str(len(input)))
            istream.write(input)
            istream.seek(0)
        verb = None
        if self.__verb:
            verb = u'_verb=%s' % self.__verb
        query = u'&'.join([s for s in [verb, self.__query] if s])

        return conditional_dict(lambda k, v: v is not None, 
                                {u'REQUEST_METHOD': self.__method, 
                                u'QUERY_STRING': query,
                                u'SCRIPT_NAME': script_name, 
                                u'PATH_INFO': path,
                                u'CONTENT_TYPE': self.__content_type,
                                u'CONTENT_LENGTH': length,
                                u'SERVER_NAME': self.__server_name.split(u'//')[-1],
                                u'SERVER_PORT': unicode(self.__server_port),
                                u'SERVER_PROTOCOL': u'HTTP/1.1',
                                u'wsgi.input': istream, 
                                u'wsgi.run_once': False,
                                u'wsgi.multithread': self.__multithread,
                                u'wsgi.multiprocess': self.__multiprocess,
                                u'wsgi.version': (1,0),
                                u'wsgi.url_scheme': self.__url_scheme,
                                })


    def _validate_input(self, input):
        if self.__method in (u'GET', u'HEAD', u'DELETE') and input is not None:
            throw_caty_exception(u'InvalidInput', u'Input must be null')
        if self.__method in (u'GET', u'HEAD', u'DELETE') and self.__content_type:
            throw_caty_exception(u'InvalidInput', u'content-type can not be specified')
        if self.__method in (u'PUT', u'POST') and input is None:
            throw_caty_exception(u'InvalidInput', u'Input must not be null')

    def _fill_default_value(self):
        from caty import UNDEFINED
        system = self.current_app._system
        if self.__server_name is UNDEFINED:
            self.__server_name = system._global_config.server_name
        if self.__server_port is UNDEFINED:
            self.__server_port = system._global_config.server_port

class ReqToEnv(Builtin):
    def execute(self, req):
        self._validate_input(req)
        if not 'contentType' in req:
            req['contentType'] = u'text/plain' if isinstance(req['body'], unicode) else u'application/octet-stream'
        chunk = req['path'].strip(u'/').split(u'/')
        path = req['path']
        system = self.current_app._system
        script_name = self.current_app.name
        istream = StringIO()
        if len(chunk) >= 2 and req['fullpath']:
            top = chunk.pop(0)
            if top in system.app_names and top not in (u'caty', u'global'):
                script_name = top
            path = u'/' + u'/'.join(chunk)
        elif script_name == u'root':
            script_name = u''
        input = req['body']
        if isinstance(input, unicode):
            input = input.encode(req.get('encoding') or self.current_app.encoding)
        length = u''
        if input:
            length = unicode(str(len(input)))
            istream.write(input)
            istream.seek(0)
        verb = None
        queries = []
        if req['verb']:
            verb = u'_verb=%s' % req['verb']
        if req['query']:
            if isinstance(req['query'], dict):
                for k, v in req['query'].items():
                    queries.append('%s=%s' % (k, v))
            else:
                queries = [req['query']]
        query = u'&'.join([s for s in [verb] + queries if s])

        r = conditional_dict(lambda k, v: v is not None, 
                                {u'REQUEST_METHOD': req['method'], 
                                u'QUERY_STRING': query,
                                u'SCRIPT_NAME': script_name, 
                                u'PATH_INFO': path,
                                u'CONTENT_TYPE': req['contentType'],
                                u'CONTENT_LENGTH': length,
                                u'SERVER_NAME': system._global_config.server_name.split(u'//')[-1],
                                u'SERVER_PORT': unicode(system._global_config.server_port),
                                u'SERVER_PROTOCOL': u'HTTP/1.1',
                                u'wsgi.input': istream, 
                                u'wsgi.run_once': False,
                                u'wsgi.multithread': True,
                                u'wsgi.multiprocess': False,
                                u'wsgi.version': (1,0),
                                u'wsgi.url_scheme': u'http',
                                })
        if req.get('cookie'):
            r['cookie'] = req['cookie']
        r.update(req.get('header', {}))
        return r


    def _validate_input(self, req):
        method = req['method']
        input = req['body']
        if method in (u'GET', u'HEAD', u'DELETE') and input is not None:
            throw_caty_exception(u'InvalidInput', u'Input must be null')
        if method in (u'GET', u'HEAD', u'DELETE') and req.get('contentType'):
            throw_caty_exception(u'InvalidInput', u'content-type can not be specified')
        if method in (u'PUT', u'POST') and input is None:
            throw_caty_exception(u'InvalidInput', u'Input must not be null')


class CallApplication(Builtin):
    def setup(self, opts):
        self.__no_middle = opts['no-middle']

    def execute(self, environ):
        environ['REMOTE_ADDR'] = u'127.0.0.1'
        environ['SERVER_PORT'] = str(environ['SERVER_PORT'])
        system = self.current_app._system
        if self.__no_middle:
            wsgi_app_cls = InternalCatyApp
        else:
            server_module_name = system.server_module_name
            exec 'import %s as server_module' % server_module_name
            wsgi_app_cls = server_module.get_app_class()
        path = environ['PATH_INFO']
        app_name = environ['SCRIPT_NAME'] or u'root'
        del environ['SCRIPT_NAME']
        app = system.get_app(app_name)
        if app_name != u'root':
            path = u'/%s%s' % (app_name, path) if path else u'/%s/' % app_name
        environ['PATH_INFO'] = path
        response_handler = ResponseHandler()
        wsgi_app = system._global_config.session.wrapper(
                            wsgi_app_cls(app, system.debug, system),
                            system._global_config.session.conf)
        output = wsgi_app.start(environ, response_handler.start_response)
        return response_handler.make_response(output)

class ResponseHandler(object):
    def __init__(self):
        self.status = None
        self.headers = {}

    def start_response(self, status, headers, exc_info=None):
        from types import StringType
        assert type(status) is StringType,"Status must be a string"
        assert len(status)>=4,"Status must be at least 4 characters"
        assert int(status[:3]),"Status message must begin w/3-digit code"
        assert status[3]==" ", "Status message must have a space after code"
        for name,val in headers:
            assert type(name) is StringType,"Header names must be strings"
            assert type(val) is StringType,"Header values must be strings"
        self.status = status
        for a, b in headers:
            self.headers[a] = unicode(b)
        return self.make_response

    def make_response(self, data):
        return {
            u'status': int(self.status.split(' ')[0]),
            u'header': self.headers,
            u'body': ''.join(data)
        }

class ProcessEnv(Builtin):

    def execute(self, environ):
        system = self.current_app._system
        server_module_name = system.server_module_name
        exec 'import %s as server_module' % server_module_name
        handler = server_module.get_handler_class()(None)
        return handler.process_env(environ)

class Perform(Builtin):
    def execute(self, environ):
        environ['REMOTE_ADDR'] = u'127.0.0.1'
        environ['SERVER_PORT'] = str(environ['SERVER_PORT'])
        system = self.current_app._system
        wsgi_app_cls = InternalCatyApp
        path = environ['PATH_INFO']
        app_name = environ['SCRIPT_NAME'] or u'root'
        del environ['SCRIPT_NAME']
        app = system.get_app(app_name)
        if app_name != u'root':
            path = u'/%s%s' % (app_name, path) if path else u'/%s/' % app_name
        environ['PATH_INFO'] = path
        environ['caty.session'] = system._global_config.session.storage.create_session(environ)
        wsgi_app = wsgi_app_cls(app, system.debug, system)
        return wsgi_app.main(environ)

class Lookup(Builtin):
    def execute(self, environ):
        system = self.current_app._system
        environ['REMOTE_ADDR'] = u'127.0.0.1'
        environ['SERVER_PORT'] = str(environ['SERVER_PORT'])
        app_name = environ['SCRIPT_NAME'] or u'root'
        del environ['SCRIPT_NAME']
        app = system.get_app(app_name)
        oldpath = environ['PATH_INFO']
        if app_name != u'root':
            path = u'/%s%s' % (app_name, oldpath) if oldpath else u'/%s/' % app_name
        else:
            path = oldpath
        environ['PATH_INFO'] = path
        environ['caty.session'] = system._global_config.session.storage.create_session(environ)
        wsgi_app = InternalCatyApp(app, system.debug, system)
        entry, input = wsgi_app.get_action_and_input(environ)
        environ['PATH_INFO'] = oldpath
        return {
            u'app': app_name,
            u'setEnv': environ,
            u'clearEnv': True,
            u'callable': entry.canonical_name,
            u'arg0': oldpath,
            u'input': input
        }

from caty.front.web.app import CatyApp, HTTP_STATUS

class InternalCatyApp(CatyApp):
    def _end_proc(self, json, headers, start_response):
        status = 200
        status = HTTP_STATUS[json.get('status', 200)]
        start_response(status, headers)
        if 'body' in json:
            b = json['body']
            return [b]
        else:
            return []

    def get_action_and_input(self, environ):
        from caty.core.handler import RequestHandler
        path = environ['PATH_INFO']
        query = self._get_query(environ)
        raw_input = environ['wsgi.input'].read(int(environ['CONTENT_LENGTH'] or 0))
        input, options, method, environ = self._process_env(raw_input, query, environ)
        
        if method not in (u'POST', u'PUT'):
            input = None
        facilities = self._app.create_facilities(lambda : environ['caty.session'])
        del environ['PATH_INFO'] # init_envで生PATH_INFOを使わせない
        if self._system.wildcat:
            self._app.init_env(facilities, self.is_debug, [u'web', u'test'], self._system, environ)
        else:
            self._app.init_env(facilities, self.is_debug, [u'web'], self._system, environ)
        handler = RequestHandler(facilities['interpreter'], 
                                 facilities['env'],
                                 self._app)
        path, _ = handler._create_path_and_vpath(path)
        entry = handler._verb_dispatcher.get(handler._file, path, options.pop('_verb', u''), environ['REQUEST_METHOD'], False)
        return entry, input


