from decimal import Decimal

from caty.command import Command
from caty.core.exception import throw_caty_exception
from caty.jsontools import tagged, obj2path, untagged, split_tag, path2obj, prettyprint, stdjson
from caty.core.std.command.builtin import TypeCalculator
from caty.core.schema import JsonSchemaError

CT_JSON = u'application/json'
CT_FORM = u'application/x-www-form-urlencoded'
CT_MULTI = u'multipart/form-data'
CT_TEXT = u'text/plain'
CT_BIN = u'application/octet-stream'


class Untranslate(Command):
    def setup(self, opts):
        self.__format = opts['format']
        self.__type = opts.get('type')

    def execute(self, data):
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
                    v = str(v)
                if k[2:] not in r:
                    r[k[2:]] = [v]
                else:
                    r[k[2:]].append(v)
        return r

class Translate(Command, TypeCalculator):
    def setup(self, opts):
        self.__type = opts.get('type')
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
                    scm = self.schema['string']
                elif t == 'bytes':
                    scm = self.schema['binary']
                scm.validate(v)
                return v
            except JsonSchemaError, e:
                er = untagged(self.error_report(e))
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
        tag, data = split_tag(generic_data)
        if self.__content_type is None:
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
        return '&'.join(r)

class Parse(Command):
    def setup(self, opts):
        self.__content_type = opts.get('content-type', self.env.get('CONTENT_TYPE', CT_JSON))
        self.__format = opts.get('format')

    def execute(self, raw_data):
        type = self.__content_type
        if self.__format is not None:
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
            return tagged('binary', raw_data)
        elif type.startswith('text/'):
            return tagged('text', raw_data)
        elif type == CT_JSON:
            if isinstance(raw_data, str):
                data = unicode(raw_data, cs)
            else:
                data = raw_data
            return tagged('text', stdjson.loads(dara))
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
                v = fs[k]
                if isinstance(v.value, (list, tuple)):
                    o[k] = self._to_unicode(v.value, cs)
                elif hasattr(v, 'filename') and v.filename:
                    o[k + ".filename"] = [unicode(v.filename, cs)]
                    o[k + ".data"] = [v.file.read()]
                else:
                    o[k] = self._to_unicode([v.value], cs)
            return  tagged(u'form', o)
        else:
            return tagged('binary', raw_data)

    def _to_unicode(self, seq, cs):
        return [unicode(v, cs) if not isinstance(v, unicode) else v for v in seq]



