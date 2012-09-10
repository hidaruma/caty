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
            path = u'/' + u'/'.join(chunk[1:])
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

        return conditional_dict(lambda k, v: v, 
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



