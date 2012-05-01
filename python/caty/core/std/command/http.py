#coding: utf-8
from caty.core.command import Builtin
from caty.core.exception import *
name='http'
schema=''
class Found(Builtin):

    def setup(self, path):
        self._path = path

    def execute(self):

        return {
            'status': 302,
            'header': {
                'Location': self._path
            }
        }

class Forbidden(Builtin):

    def setup(self, path):
        self._path = path

    def execute(self):
        raise CatyException(
            'HTTP_403',
            u'Can not access to $path',
            path=self._path
        )

class NotFound(Builtin):

    def setup(self, path):
        self._path = path

    def execute(self):
        raise CatyException(
            'HTTP_404', 
            u'File does not exists: $path',
            path=self._path
            )


class BadRequest(Builtin):

    def setup(self, path, method):
        self._path = path
        self._method = method

    def execute(self):
        raise CatyException(
            'HTTP_400', 
            u'Bad Access: path=$path, method=$method',
            path=self._path,
            method=self._method
            )

class NotAllowed(Builtin):

    def setup(self, path, method):
        self._path = path

    def execute(self):
        raise CatyException(
            'HTTP_405', 
            u'HTTP method `$mthod` is not allowed for `$path`',
            path=self._path
            )

class URLEncode(Builtin):
    def setup(self, opts):
        self._encoding = opts['encoding']

    def execute(self, input):
        import caty.jsontools as json
        import urllib
        o = {}
        for k, v in json.obj2path(input).items():
            k = k.replace('$.', '')
            if v is None:
                continue
            if isinstance(v, unicode):
                v = v.encode(self._encoding)
            elif not isinstance(v, str):
                v = json.stdjson.dumps(v).encode(self._encoding)
            o[k] = v
        return unicode(urllib.urlencode(o))
