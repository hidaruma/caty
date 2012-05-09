from caty.command import Command
from caty.jsontools import tagged, obj2path

class Untranslate(Command):
    def setup(self, opts):
        self.__format = opts['format']
        self.__type = opts.get('type')

    def execute(self, data):
        if self.__format == 'form':
            conv = self.__convert_to_form(data)
            return tagged(self.__format, conv)
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

