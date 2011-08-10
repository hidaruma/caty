#coding:utf-8
from caty.util import merge_dict
from caty.template.core.exceptions import *
from caty.jsontools.path import build_query

class Context(object):
    u"""変数参照用の名前空間。
    辞書に対するラッパーであり、 a.b.c のような階層アクセスを実装する。
    また、ラップ対象の辞書は単一の辞書ではなく辞書のリストであり、
    複数の辞書に同一のキーが存在する場合、最初に見つかったものを返すこととする。
    これは for-each に類する構文の実現のために用いる。
    """
    def __init__(self, dictionaly, default_ctx=True):
        self.dict = [dictionaly]
        self.default_ctx = default_ctx

    def __getitem__(self, key):
        q = build_query('$.' + key)
        for d in self.dict:
            try:
                r = q.find(d)
                v = r.next()
            except:
                continue
            else:
                return v
        raise TemplateRuntimeError('Undefined variable: %s, current context= %s' % (key, repr(self.dict)))

    def get(self, *args):
        key = args[0]
        try:
            return self[key]
        except:
            if len(args) > 1:
                return args[1]
            else:
                raise
                
    def new(self, new_context):
        u"""コンテキストに新たな辞書を追加する。
        もしもコンテキストが空だった場合、何もしない。
        """
        self.dict.insert(0, new_context)

    def is_context_list_length_gt1(f):
        u"""コンテキストの内包する辞書のリストが1以上でなかった場合エラーとする。
        """
        def _(self, *args, **kwds):
            if len(self.dict) < 2 and self.default_ctx:
                raise TemplateRuntimeError('Can not modify default context')
            return f(self, *args, **kwds)
        return _

    @is_context_list_length_gt1
    def delete(self):
        u"""コンテキストの辞書リストの先頭を削除する。
        """
        self.dict.pop(0)

    @is_context_list_length_gt1
    def __setitem__(self, name, value):
        u"""辞書リストの先頭の辞書に新たな要素を追加する。
        a.b.c のような階層化された name が与えられた場合、
        それらは a: {b: c: value}} という辞書に変換される。
        """
        d = reduce(lambda x, y: {y: x}, reversed(name.split('.') + [value]))
        if d.keys()[0] not in self.dict[0] or not isinstance(d.values()[0], dict):
            self.dict[0][d.keys()[0]] = d.values()[0]
        else:
            self.dict[0][d.keys()[0]] = merge_dict(self.dict[0][d.keys()[0]], d.values()[0])
    
    @is_context_list_length_gt1
    def __delitem__(self, key):
        del self.dict[0][key]

    def merge(self, newdict):
        u"""辞書リストの先頭に新たな辞書をマージする。
        """
        self.dict[0] = merge_dict(self.dict[0], newdict)
    
    def __str__(self):
        return '\n'.join(repr(i) for i in self.dict)

class StringWrapper(unicode):
    def __init__(self, s):
        if isinstance(s, StringWrapper):
            self.string = s.string
        else:
            self.string = s

    def get_string(self):
        return self.string

    @property
    def type(self):
        raise NotImplemtedError()

class RawString(StringWrapper):
    u"""Unicode データのラッパークラス。
    """
    @property
    def type(self):
        return 'raw'

class VariableString(StringWrapper):
    u"""Unicode データのラッパークラス。
    テンプレートコンテキストから取り出された変数が文字列型の場合、
    一旦このクラスに変換される。
    実際にどのような処理を行うかはレンダラーが決める。
    """
    @property
    def type(self):
        return 'var'

class DummyContext(object):
    def __init__(self, key):
        self.key = key

    def __str__(self):
        return '$'+self.key

    def __iter__(self):
        return iter([self])

