#coding: utf-8
from decimal import Decimal

from caty.command import Command
from caty.core.exception import throw_caty_exception
from caty.jsontools import tagged, obj2path, untagged, split_tag, path2obj, prettyprint, stdjson
from caty.core.std.command.builtin import TypeCalculator
from caty.core.schema import JsonSchemaError
from caty import UNDEFINED

CT_JSON = u'application/json'
CT_FORM = u'application/x-www-form-urlencoded'
CT_MULTI = u'multipart/form-data'
CT_TEXT = u'text/plain'
CT_BIN = u'application/octet-stream'


class UnConstrue(Command):
    def setup(self, opts):
        self.__format = opts['format']
        self.__type = opts.get('type')

    def execute(self, data):
        if data is None:
            return tagged(u'void', None)
        if self.__format == 'form':
            conv = self.__convert_to_form(data)
            return tagged(self.__format, conv)
        elif self.__format == 'text':
            if not isinstance(data, unicode):
                self.__throw(u'not a string', data)
            return tagged(u'text', data)
        elif self.__format == 'bytes':
            if not isinstance(data, str):
                self.__throw(u'not a binary', data)
            return tagged(u'bytes', data)
        else:
            return tagged(self.__format, data)

    def __throw(self, er, data):
        if self.__type:
            throw_caty_exception('ConversionError', u'failed to untranslate $type:\n$errorObj\nsource:$source', errorObj=er, source=data, type=self.__type)
        else:
            throw_caty_exception('ConversionError', u'failed to convert:\n$errorObj\nsource:$source', errorObj=er, source=data)

    def __convert_to_form(self, data):
        r = {}
        if not isinstance(data, dict):
            throw_caty_exception(u'BadInput', '$data', data=data)
        for k, v in obj2path(data).items():
            if k.endswith('.{}') or k.endswith('.[]') or v is None or v == u'': 
                # 空のオブジェクトor配列、空文字列、nullはフォーム経由で送れない。
                # エラーにすべきかは微妙な所ではある。
                pass
            else:
                if k.rstrip('0123456789').endswith('.'):
                    # 配列項目は一つにまとめ直す。
                    k = k.rstrip('0123456789.')
                if not isinstance(v, basestring):
                    if isinstance(v, bool):
                        v = unicode(str(v)).lower()
                    else:
                        v = unicode(str(v))
                if k[2:] not in r:
                    r[k[2:]] = [v]
                else:
                    r[k[2:]].append(v)
        return r

class Construe(Command, TypeCalculator):
    def setup(self, opts):
        self.__type = opts.get('type')
        self.mod = UNDEFINED
        if self.__type:
            self.set_schema(self.__type)

    def execute(self, generic_data):
        if not self.__type:
            return untagged(generic_data)
        else:
            try:
                if generic_data is None:
                    n = None
                    scm = self.converter
                    scm.validate(n)
                    return n
                t, v = split_tag(generic_data)
                scm = self.converter
                if t == 'form':
                    return scm.convert(_to_nested(v))
                elif t == 'json':
                    n = scm.fill_default(v)
                    scm.validate(n)
                    return n
                elif t == 'text':
                    scm = self.schema.get_type('string')
                elif t == 'bytes':
                    scm = self.schema.get_type('binary')
                elif t == 'void':
                    scm = self.schema.get_type('null')
                scm.validate(v)
                return v
            except JsonSchemaError, e:
                er = untagged(e.error_report(self.i18n))
                if self.__type:
                    throw_caty_exception('ConversionError', u'failed to convert data to $type:\n$errorObj\nsource:$source', errorObj=er, source=generic_data, type=self.__type)
                else:
                    throw_caty_exception('ConversionError', u'failed to convert data:\n$errorObj\nsource:$source', errorObj=er, source=generic_data)

def _to_nested(input):
    d = {}
    for k, v in input.items():
        d['$.'+k] = v
    return path2obj(d) if d else d

class Unparse(Command):
    def setup(self, opts):
        self.__content_type = opts.get('content-type')

    def execute(self, generic_data):
        if self.__content_type is UNDEFINED and self.env.exists('CONTENT_TYPE'):
            self.__content_type = self.env.get('CONTENT_TYPE')
        tag, data = split_tag(generic_data)
        if tag == 'void':
            return None
        if self.__content_type is UNDEFINED:
            if tag == 'form':
                self.__content_type = CT_FORM
            elif tag == 'json':
                self.__content_type = CT_JSON
            elif tag == 'text':
                self.__content_type = CT_TEXT
            else:
                self.__content_type = CT_BIN
        if self.__content_type == CT_FORM:
            if isinstance(data, object):
                return self._encode_to_form(data)
            else:
                raise
        elif self.__content_type == 'multipart/form-data':
            raise NotImplementedError()
        elif self.__content_type == CT_JSON:
            return prettyprint(data)
        elif self.__content_type.startswith('text/'):
            if isinstance(data, basestring):
                return data
            elif isinstance(data, bool):
                return str(bool).lower()
            elif isinstance(data, (int, Decimal)):
                return str(data)
            else:
                return prettyprint(data)
        else:
            if isinstance(data, str):
                return data
            elif isinstance(data, unicode):
                return data.encode(self.env.get('APP_ENCODING', 'utf-8'))
            elif isinstance(data, bool):
                return str(bool).lower()
            elif isinstance(data, (int, Decimal)):
                return str(data)
            else:
                return prettyprint(data).encode(self.env.get('APP_ENCODING', 'utf-8'))

    def _encode_to_form(self, data):
        import urllib
        r = []
        for k, v in data.items():
            for i in v:
                if isinstance(i, unicode):
                    i = i.encode(self.env.get('APP_ENCODING', 'utf-8'))
                r.append(urllib.urlencode({k: i}))
        return unicode('&'.join(r))

class Parse(Command):
    def setup(self, opts):
        self.__content_type = opts.get('content-type')
        self.__format = opts.get('format')

    def execute(self, raw_data):
        if raw_data is None:
            return tagged('void', None)
        if self.__content_type is UNDEFINED and self.env.exists('CONTENT_TYPE'):
            self.__content_type = self.env.get('CONTENT_TYPE')
        type = self.__content_type
        if type is UNDEFINED:
            if isinstance(raw_data, str):
                type = CT_BIN
            else:
                type = CT_TEXT
        if self.__format is not UNDEFINED:
            if self.__format == 'json':
                type = CT_JSON
            elif self.__format == 'text':
                type = CT_TEXT
            elif self.__format == 'form':
                type = CT_FORM
            else:
                type = CT_BIN
        if ';' in type:
            type, rest = map(unicode.strip, type.split(';', 1))
            if rest.startswith('charset'):
                cs = rest.split('=').pop(1)
        else:
            cs = self.env.get('APP_ENCODING', 'utf-8')
        if type == CT_BIN:
            if not isinstance(raw_data, str):
                raw_data = raw_data.encode(cs)
            return tagged('bytes', raw_data)
        elif type.startswith('text/'):
            return tagged('text', raw_data)
        elif type == CT_JSON:
            if isinstance(raw_data, str):
                data = unicode(raw_data, cs)
            else:
                data = raw_data
            if not raw_data:
                data = '{}'
            return tagged('json', stdjson.loads(data))
        elif type == CT_FORM or type == CT_MULTI:
            import cgi
            from StringIO import StringIO
            input = StringIO(raw_data)
            input.seek(0)
            env = {}
            env.update(self.env._dict)
            if 'REQUEST_METHOD' not in env:
                env['REQUEST_METHOD'] = 'POST'
            env['CONTENT_LENGTH'] = len(raw_data)
            env['CONTENT_TYPE'] = type

            if 'QUERY_STRING' in env:
                del env['QUERY_STRING']
            fs = cgi.FieldStorage(fp=input, environ=env)
            o = {}
            for k in fs.keys():
                vs = fs[k]
                if not isinstance(vs, list):
                    vs = [vs]
                if not k in o:
                    o[k] = []
                for v in vs:
                    if isinstance(v.value, (list, tuple)):
                        o[k].extend(self._to_unicode(v.value, cs))
                    elif hasattr(v, 'filename') and v.filename:
                        o[k + ".filename"] = [unicode(v.filename, cs)]
                        o[k + ".data"] = [v.file.read()]
                    else:
                        o[k].extend(self._to_unicode([v.value], cs))
            return  tagged(u'form', o)
        else:
            return tagged('bytes', raw_data)

    def _to_unicode(self, seq, cs):
        return [unicode(v, cs) if not isinstance(v, unicode) else v for v in seq]


from caty.core.command import Builtin
from caty.core.exception import *

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

