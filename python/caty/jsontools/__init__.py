# coding: utf-8
u"""JSON 関連のユーティリティ。
Python のバージョン間で JSON ライブラリの有無が違うことへの対処、
JSON オブジェクトへのスキーマ適用などの処理などを行う。
"""

try:
    import json
except:
    try:
        import simplejson as json
    except:
        raise ImportError('Python 2.6 (or later) or simplejson package is needed')
import caty.core.runtimeobject as ro
from caty import UNDEFINED
import decimal
__all__ = ['load', 
           'loads', 
           'dump', 
           'dumps', 
           'decode',
           'encode',
           'prettyprint', 
           'PPEncoder',
           'pp', 
           'TaggedValue',
           'TagOnly',
           'tag',
           'obj2path',
           'path2obj',
           'tagged',
           'untagged',
           'split_tag',
           'CatyEncoder',
           'raw_json']

raw_json = json

class JsonError(Exception): pass

from caty.util import deprecated
def load(fo):
    u"""ファイル類似オブジェクトより JSON データをロードする。
    """
    return decode(json.load(fo, parse_float=decimal.Decimal))

@deprecated(u'stdjsonかxjsonを使うこと')
def loads(s):
    u"""文字列より JSON データをロードする。
    """
    return decode(json.loads(s, parse_float=decimal.Decimal))

@deprecated(u'stdjsonかxjsonを使うこと')
def dump(obj, fo, **kwds):
    return json.dump(encode(obj), fo, cls=CatyEncoder, **kwds)

@deprecated(u'stdjsonかxjsonを使うこと')
def dumps(obj, **kwds):
    return json.dumps(encode(obj), cls=CatyEncoder, **kwds)

class CatyEncoder(json.encoder.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return InternalDecimal(o)
        else:
            return json.encoder.JSONEncoder.default(self, o)
    
    def encode(self, o):
        if isinstance(o, str):
            return u'b"%s"' % repr(o)[1:-1]
        else:
            return json.encoder.JSONEncoder.encode(self, o)

    def _iterencode(self, o, markers=None):
        if isinstance(o, str):
            yield u'b"%s"' % repr(o)[1:-1]
        elif o is UNDEFINED:
            pass
        else:
            for v in json.encoder.JSONEncoder._iterencode(self, o, markers):
                yield v

class InternalDecimal(float):
    u"""simplejson の JSONEncoder は、 default をオーバーライドした結果をさらにエンコードするようになっている。
    そのため、 Decimal 型をエンコードしようとするときに default メソッド内部で文字列にすると、
    その結果を文字列としてさらにエンコードされるため、デコード処理の際に Decimal ではなく文字列とされてしまう。
    JSONEncoder に Decimal のエンコードをさせるため、このクラスでラップする。
    """
    def __init__(self, v):
        self.__value = v
        
    def __repr__(self):
        return str(self.__value)

class _EMPTY(object): pass
_empty = _EMPTY()

class PPEncoder(CatyEncoder):
    u"""prettyprint時にタグ型があるとjsonライブラリのdumpsが使えない。
    そのため、タグ型のみをこのクラスでハンドルする必要がある。
    """
    def default(self, o):
        if isinstance(o, TaggedValue):
            return o
        elif isinstance(o, TagOnly):
            return u'@%s' % (o.tag)
        else:
            return CatyEncoder.default(self, o)
    
    def _iterencode(self, o, markers=None):
        if isinstance(o, TaggedValue):
            t, v = split_tag(o)
            yield u'@%s ' % t
            for e in self._iterencode(v, markers):
                yield e
        elif isinstance(o, TagOnly):
            yield u'@%s' % (o.tag)
        elif not isinstance(o, (basestring, bool, int, decimal.Decimal, InternalDecimal, dict, list, tuple)) and o is not None:
            from caty import UNDEFINED
            if o is UNDEFINED:
                yield u"#'undefined"
            elif o is _empty:
                yield u''
            else:
                yield u'#<foreign %s>' % repr(o)
        else:
            for e in CatyEncoder._iterencode(self, self.__normalize(o), markers):
                yield e

    def __normalize(self, o):
        if isinstance(o, (tuple, list)):
            return self.__erase_undef(o)
        elif isinstance(o, dict):
            return self.__reduce_undef(o)
        else:
            return o

    def __erase_undef(self, r):
        from caty import UNDEFINED
        import itertools
        l = itertools.dropwhile(lambda x: x==UNDEFINED, reversed(r))
        return [(self.__normalize(a) if a is not UNDEFINED else _empty) for a in reversed(list(l))]

    def __reduce_undef(self, o):
        r = {}
        for k, v in o.items():
            if v is UNDEFINED:
                pass
            else:
                r[k] = self.__normalize(v)
        return r

def encode(obj):
    u"""Caty 内部形式から JSON 標準形式へと変換する。
    """
    if isinstance(obj, TaggedValue):
        return {'$$tag': obj.tag, '$$val': encode(obj.value)}
    elif isinstance(obj, TagOnly):
        return {'$$tag': obj.tag, '$$no-value': True}
    elif isinstance(obj, dict):
        n = {}
        for k, v in obj.items():
            n[k] = encode(v)
        return n
    elif isinstance(obj, (list, tuple)):
        return map(encode, obj)
    else:
        return obj

def decode(obj):
    u"""標準の JSON 形式から Caty 内部形式へと変換する。
    内部形式ではタグの扱いが異なる。
    """
    if isinstance(obj, dict):
        if '$$tag' in obj:
            if '$$val' in obj:
                return TaggedValue(obj['$$tag'], decode(obj['$$val']))
            elif '$$no-value' in obj:
                return TagOnly(obj['$$tag'])
            else:
                raise JsonError(ro.i18n.get(u'No $$val or $$no-value that matches to $$tag'))
        else:
            n = {}
            for k, v in obj.items():
                n[k] = decode(v)
            return n
    elif isinstance(obj, (list, tuple)):
        return map(decode, obj)
    else:
        if isinstance(obj, str):
            return unicode(obj)
        else:
            return obj

def prettyprint(obj, depth=0, encoding=None):
    v = json.dumps(obj, cls=PPEncoder, indent=4, ensure_ascii=False)
    if isinstance(v, unicode):
        return v
    else:
        return unicode(str(v))

pp = prettyprint

import types
import caty
_tag_class_dict = {
    int: u'number',
    decimal.Decimal: u'number',
    bool: u'boolean',
    dict: u'object',
    unicode: u'string',
    str: u'binary',
    types.NoneType: u'null',
    list: u'array',
    tuple: u'array',
    caty.UNDEFINED.__class__: u'undefined',
}

_reserved = set(_tag_class_dict.values())
_reserved.add('integer')
_reserved.add('foreign')

_builtin_types = dict()
for a, b in _tag_class_dict.items():
    if b not in _builtin_types:
        _builtin_types[b] = [a]
    else:
        _builtin_types[b].append(a)
_builtin_types['number'].append(int)
_builtin_types['integer'] = [int]

class _anything_else(object):
    def __contains__(self, tp):
        return tp not in _tag_class_dict
_builtin_types['foreign'] = _anything_else()

class TaggedValue(object):
    """type tag 付きのスカラー値用のクラス。
    {$tag:foo, $val:1} のようなオブジェクトは、あくまでもスカラー値として扱いたい。
    そのため、タグ付きのデータはすべて {} や dict などではなく
    専用のタグ型によって表現する。
    """
    def __init__(self, t, v):
        self.__tag = t
        self.__value = v

    @property
    def value(self):
        return self.__value

    @property
    def tag(self):
        return self.__tag

    def __str__(self):
        return u'@%s %s' % (self.tag, str(self.value))

    def __eq__(self, o):
        return self.tag == tag(o) and self.value == untagged(o)

class TagOnly(object):
    u"""タグのみを持ち、対応する値は存在しない値。
    JSON には {$tag: "...", $no-value:true} の形式でエンコードされる。
    """
    def __init__(self, tag):
        self.tag = tag

    @property
    def value(self):
        return UNDEFINED

    def __eq__(self, o):
        return isinstance(o, TagOnly) and self.tag == tag(o)

def tagged(tagname, val=UNDEFINED):
    if tagname in _reserved:
        if not type(val) in _builtin_types[tagname]:
            raise JsonError(ro.i18n.get(u'$keyword is reserved tag', keyword=tagname))
        else:
            return val
    if val is UNDEFINED:
        return TagOnly(tagname)
    r = TaggedValue(tagname, val)
    return r

def tag(val, explicit=False):
    try:
        return val.tag
    except:
        if explicit:
            raise JsonError(ro.i18n.get(u'No explicit tag'))
        t = type(val)
        return _tag_class_dict.get(t, u'foreign')

def untagged(val, explicit=False):
    try:
        return val.value
    except:
        if explicit:
            raise JsonError(ro.i18n.get('No explicit tag'))
        return val

def split_tag(val):
    return tag(val), untagged(val)

def obj2path(obj):
    u"""辞書形式の JSON オブジェクトをパス形式に変換する。
    パス形式の JSON は深さが 1 の辞書となり、
    入れ子関係はすべてフラットにされてキーの値がパス情報となる。
    すなわち以下のオブジェクトは

    {
        "a": 1,
        "b": {
            "c": 2
        }
    }

    このような形式に変換される。

    {
        "a": 1,
        "b.c": 2
    }
    """
    assert isinstance(obj, dict)
    def flatten(obj, parent='$'):
        if isinstance(obj, dict):
            n = 0
            for k, v in obj.items():
                n += 1
                for r in flatten(v, parent + '.' + k):
                    yield r
            if n == 0: # 空のオブジェクト
                yield parent + '.' + '{}', None
        elif isinstance(obj, (list, tuple)):
            n = 0
            for i, v in enumerate(obj):
                n += 1
                for r in flatten(v, parent + '.' + str(i)):
                    yield r
            if n == 0:# 空のリスト
                yield parent + '.' + '[]', None
        else:
            yield parent, obj
    p = {}
    p.update(list(flatten(obj)))
    return p

from caty.util import merge_dict, try_parse
def path2obj(obj):
    u"""パス形式のオブジェクトを入れ子構造に戻す。
    """
    assert isinstance(obj, dict)
    def split_path(o):
        for k, v in o.items():
            k = k[2:] # $. の削除
            keys = k.split('.')
            if keys[-1] == '[]':
                keys.pop(-1)
                v = []
            elif keys[-1] == '{}':
                keys.pop(-1)
                v = {}
            yield reduce(lambda x, y: {y: x}, reversed(keys + [v]))
    
    def merge_path(o):
        return reduce(lambda a, b: merge_dict(a, b), split_path(o))

    def is_array(v):
        return try_parse(int, v.keys()[0]) != None
    
    def make_array(o):
        l = range(len(o))
        for k, v in o.items():
            l[int(k)] = make_tree(v)
        return l
    
    def make_obj(tree):
        o = {}
        for k, v in tree.items():
            o[k] = make_tree(v)
        return o
    
    def make_tree(o):
        if isinstance(o, dict):
            if is_array(o):
                return make_array(o)
            return make_obj(o)
        else:
            return o

    return make_tree(merge_path(obj))

import types
def is_json(obj):
    if isinstance(obj, (int, decimal.Decimal, unicode, str, bool, types.NoneType)):
        return True
    elif isinstance(obj, dict):
        return all(map(is_json, obj.values()))
    elif isinstance(obj, list):
        return all(map(is_json, obj))
    else:
        return False


class SelectionFixer(object):
    def __init__(self, schema):
        self.schema = schema

    def fix(self, input):
        if isinstance(input, (dict, list, tuple)):
            return self._expand_embed(self._fix(input))
        else:
            return input

    def _fix(self, input):
        from caty.core.exception import CatyException, throw_caty_exception
        from caty.util import error_to_ustr
        scm = self.schema['json:selection']
        if isinstance(input, dict):
            if '$selection' in input:
                try:
                    scm.validate(input)
                    tp = input['$selection'], type(input['$current']), type(input['$values'])
                    if tp not in ((u'object', unicode, dict), (u'array', int, list)):
                        throw_caty_exception(u'BadSelection', 
                                         u'Invalid selection: $cause, $obj', 
                                         cause=u'miss matched',
                                         obj = input)
                    v = input['$values']
                    c = input['$current']
                    return self.fix(v[c])
                except KeyError, e:
                    c = CatyException(u'PropertyNotExist', error_to_ustr(e))
                    throw_caty_exception(u'BadSelection', 
                                         u'Invalid selection: $cause, $obj', 
                                         cause=c.tag + ':' + c.get_message(ro.i18n), 
                                         obj=json.pp(input))
                except IndexError, e:
                    c = CatyException(u'IndexOutOfRange', error_to_ustr(e))
                    throw_caty_exception(u'BadSelection', 
                                         u'Invalid selection: $cause, $obj', 
                                         cause=c.tag + ':' + c.get_message(ro.i18n), 
                                         obj=json.pp(input))
                except CatyException, e:
                    raise
                except Exception, e:
                    throw_caty_exception(u'BadSelection', 
                                         u'Invalid selection: $cause, $obj', 
                                         cause=error_to_ustr(e), 
                                         obj=json.pp(input))
            else:
                o = {}
                for k, v in input.items():
                    o[k] = self.fix(v)
                return o
        else:
            a = []
            for v in input:
                a.append(self.fix(v))
            return a

    def _expand_embed(self, obj):
        if isinstance(obj, dict):
            if '$embed' in obj:
                e = obj['$embed']
                obj.pop('$embed')
                obj.update(e)
            o = {}
            for k, v in obj.items():
                o[k] = self._expand_embed(v)
            return o
        elif isinstance(obj, list):
            l = []
            for i in obj:
                l.append(self._expand_embed(i))
            return l
        else:
            return obj


