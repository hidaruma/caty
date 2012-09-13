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
        if len(chunk) >= 2 and self.__fullpath:
            top = chunk.pop(0)
            if top in system.app_names and top not in (u'caty', u'global'):
                script_name = top
            path = u'/' + u'/'.join(chunk)
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
            verb = u'__verb=%s' % self.__verb
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
        wsgi_app = wsgi_app_cls(app, system.debug, system)
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
