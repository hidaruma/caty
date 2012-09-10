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
        self.__query = query
        self.__path = path

    def execute(self, input):
        self._validate_input(input)
        if self.__method in (u'PUT', u'POST') and not self.__content_type:
            self.__content_type = u'text/plain' if isinstance(input, unicode) else u'application/octet-stream'
        chunk = self.__path.strip(u'/').split(u'/')
        system = self.current_app._system
        script_name = self.current_app.name
        path = self.__path
        istream = StringIO()
        if len(chunk) >= 2 and self.__fullpath:
            top = chunk[0]
            if top in system.app_names and top not in (u'caty', u'global'):
                script_name = top
        elif script_name != u'root':
            path = u'/%s%s' % (script_name, path)

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
                                u'wsgi.input': istream, 
                                })


    def _validate_input(self, input):
        if self.__method in (u'GET', u'HEAD', u'DELETE') and input is not None:
            throw_caty_exception(u'InvalidInput', u'Input must be null')
        if self.__method in (u'GET', u'HEAD', u'DELETE') and self.__content_type:
            throw_caty_exception(u'InvalidInput', u'content-type can not be specified')
        if self.__method in (u'PUT', u'POST') and input is None:
            throw_caty_exception(u'InvalidInput', u'Input must not be null')

class CallApplication(Builtin):
    def setup(self, opts):
        self.__no_middle = opts['no-middle']

    def execute(self, environ):
        environ['REMOTE_ADDR'] = u'127.0.0.1'
        system = self.current_app._system
        if self.__no_middle:
            wsgi_app = InternalWSGIDispatcher(system, system.debug)
        else:
            server_module_name = system.server_module_name
            exec 'import %s as server_module' % server_module_name
            wsgi_app = server_module.get_dispatcher(system, system.debug)
        response_handler = ResponseHandler()
        output = wsgi_app(environ, response_handler.start_response)
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

from caty.front.web.app import CatyWSGIDispatcher, CatyApp, HTTP_STATUS
class InternalWSGIDispatcher(CatyWSGIDispatcher):

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        app = self.dispatch(path)
        return InternalCatyApp(app, self.is_debug, self._system).start(environ, start_response)

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
