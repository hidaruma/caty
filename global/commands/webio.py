from caty.command import Command
from caty.core.exception import throw_caty_exception
from caty.jsontools import tagged, obj2path, untagged, split_tag, path2obj
from caty.core.std.command.builtin import TypeCalculator
from caty.core.schema import JsonSchemaError

class Untranslate(Command):
    def setup(self, opts):
        self.__format = opts['format']
        self.__type = opts.get('type')

    def execute(self, data):
        if self.__format == 'form':
            conv = self.__convert_to_form(data)
            return tagged(self.__format, conv)
        elif self.__format == 'text':
            return tagged(u'text', conv)
        elif self.__format == 'bytes':
            return tagged(u'bytes', conv)
        else:
            return tagged(self.__format, data)

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
                    k = k.rstrip('0123456789')
                if not isinstance(v, basestring):
                    v = str(v)
                if k not in r:
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
                    return scm.convert(self._to_nested(v))
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
                er = self.error_report(e)
                if self.__type:
                    throw_caty_exception('ConversionError', u'failed to convert data to $type:\n$errorObj\nsource:$source', errorObj=er, source=generic_data, type=self.__type)
                else:
                    throw_caty_exception('ConversionError', u'failed to convert data:\n$errorObj\nsource:$source', errorObj=er, source=generic_data)

    def _to_nested(self, input):
        d = {}
        for k, v in input.items():
            d['$.'+k] = v
        return path2obj(d) if d else d
