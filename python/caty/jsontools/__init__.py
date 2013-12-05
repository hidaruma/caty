# coding: utf-8
u"""JSON 関連のユーティリティ。
Python のバージョン間で JSON ライブラリの有無が違うことへの対処、
JSON オブジェクトへのスキーマ適用などの処理などを行う。
"""
from __future__ import absolute_import
try:
    import json
except:
    try:
        import simplejson as json
    except:
        raise ImportError('Python 2.6 (or later) or simplejson package is needed')
import caty.core.runtimeobject as ro
from caty.core.spectypes import UNDEFINED, INDEF
import decimal
import xjson
from xjson import prettyprint, PPEncoder, pp, TaggedValue, TagOnly, tag, tagged, encode, decode, untagged, obj2path, split_tag, split_exp_tag, XJSONEncoder, normalize_number, is_json
CatyEncoder = XJSONEncoder
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
           'INDEF',
           'tag',
           'obj2path',
           'path2obj',
           'tagged',
           'untagged',
           'split_tag',
           'split_exp_tag',
           'CatyEncoder',
           'doc_pp',
           'raw_json',
           'xjson']

raw_json = json

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

class PPEncoderWithDoc(PPEncoder):
    def _make_iterencode(self, markers, _default, _encoder, _indent, _floatstr,
            _key_separator, _item_separator, _sort_keys, _skipkeys, _one_shot, iterencode,
            ## HACK: hand-optimized bytecode; turn globals into locals
            ValueError=ValueError,
            basestring=basestring,
            dict=dict,
            float=float,
            id=id,
            int=int,
            isinstance=isinstance,
            list=list,
            long=long,
            str=str,
            tuple=tuple,
        ):

        def _iterencode_list(lst, _current_indent_level):
            if not lst:
                yield '[]'
                return
            if markers is not None:
                markerid = id(lst)
                if markerid in markers:
                    raise ValueError("Circular reference detected")
                markers[markerid] = lst
            buf = '['
            if _indent is not None:
                _current_indent_level += 1
                newline_indent = '\n' + (' ' * (_indent * _current_indent_level))
                separator = _item_separator + newline_indent
                buf += newline_indent
            else:
                newline_indent = None
                separator = _item_separator
            first = True
            for value in lst:
                if first:
                    first = False
                else:
                    buf = separator
                if hasattr(value, u'docstring'):
                    yield buf + u'/* %s */' % value.docstring
                    buf = separator
                if isinstance(value, unicode):
                    yield buf + _encoder(value)
                elif value is None:
                    yield buf + 'null'
                elif value is True:
                    yield buf + 'true'
                elif value is False:
                    yield buf + 'false'
                elif isinstance(value, (int, long)):
                    yield buf + str(value)
                elif isinstance(value, float):
                    yield buf + _floatstr(value)
                else:
                    yield buf
                    if isinstance(value, (list, tuple)):
                        chunks = _iterencode_list(value, _current_indent_level)
                    elif isinstance(value, dict):
                        chunks = _iterencode_dict(value, _current_indent_level)
                    else:
                        chunks = _iterencode(value, _current_indent_level)
                    for chunk in chunks:
                        yield chunk
            if newline_indent is not None:
                _current_indent_level -= 1
                yield '\n' + (' ' * (_indent * _current_indent_level))
            yield ']'
            if markers is not None:
                del markers[markerid]

        def _iterencode_dict(dct, _current_indent_level):
            if not dct:
                yield '{}'
                return
            if markers is not None:
                markerid = id(dct)
                if markerid in markers:
                    raise ValueError("Circular reference detected")
                markers[markerid] = dct
            yield '{'
            if _indent is not None:
                _current_indent_level += 1
                newline_indent = '\n' + (' ' * (_indent * _current_indent_level))
                item_separator = _item_separator + newline_indent
                yield newline_indent
            else:
                newline_indent = None
                item_separator = _item_separator
            first = True
            if _sort_keys:
                items = sorted(dct.items(), key=lambda kv: kv[0])
            else:
                items = dct.iteritems()
            for key, value in items:
                if isinstance(key, basestring):
                    pass
                # JavaScript is weakly typed for these, so it makes sense to
                # also allow them.  Many encoders seem to do something like this.
                elif isinstance(key, float):
                    key = _floatstr(key)
                elif key is True:
                    key = 'true'
                elif key is False:
                    key = 'false'
                elif key is None:
                    key = 'null'
                elif isinstance(key, (int, long)):
                    key = str(key)
                elif _skipkeys:
                    continue
                else:
                    raise TypeError("key " + repr(key) + " is not a string")
                if first:
                    first = False
                else:
                    yield item_separator
                yield _encoder(key)
                yield _key_separator
                if isinstance(value, unicode):
                    yield _encoder(value)
                elif value is None:
                    yield 'null'
                elif value is True:
                    yield 'true'
                elif value is False:
                    yield 'false'
                elif isinstance(value, (int, long)):
                    yield str(value)
                elif isinstance(value, float):
                    yield _floatstr(value)
                else:
                    if isinstance(value, (list, tuple)):
                        chunks = _iterencode_list(value, _current_indent_level)
                    elif isinstance(value, dict):
                        chunks = _iterencode_dict(value, _current_indent_level)
                    else:
                        chunks = _iterencode(value, _current_indent_level)
                    for chunk in chunks:
                        yield chunk
            if newline_indent is not None:
                _current_indent_level -= 1
                yield '\n' + (' ' * (_indent * _current_indent_level))
            yield '}'
            if markers is not None:
                del markers[markerid]
            
        _iterencode = lambda o, _current_indent_level: iterencode(o, 
                                                           _current_indent_level, 
                                                           _iterencode_list, 
                                                           _iterencode_dict,
                                                           markers,
                                                           _encoder)
        return _iterencode


    def _erase_undef(self, o):
        from caty import UNDEFINED
        import itertools
        l = itertools.dropwhile(lambda x: x==UNDEFINED, reversed(o))
        r = o.__class__()
        for a in reversed(list(l)):
            r.append((self._normalize(a) if a is not UNDEFINED else _empty))
        if hasattr(o, 'docstring'):
            r.docstring = o.docstring
        return r

    def _reduce_undef(self, o):
        r = o.__class__()
        for k, v in o.items():
            if v is UNDEFINED:
                pass
            else:
                r[k] = self._normalize(v)
        if hasattr(o, 'docstring'):
            r.docstring = o.docstring
        return r

def doc_pp(obj):
    v = json.dumps(obj, cls=PPEncoderWithDoc, indent=4, ensure_ascii=False)
    if isinstance(v, unicode):
        return v
    else:
        return unicode(str(v))

import types
import caty
import caty.core.spectypes

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
        if v:
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
        scm = self.schema.get_type('json:selection')
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
                                         obj=pp(input))
                except IndexError, e:
                    c = CatyException(u'IndexOutOfRange', error_to_ustr(e))
                    throw_caty_exception(u'BadSelection', 
                                         u'Invalid selection: $cause, $obj', 
                                         cause=c.tag + ':' + c.get_message(ro.i18n), 
                                         obj=pp(input))
                except CatyException, e:
                    raise
                except Exception, e:
                    throw_caty_exception(u'BadSelection', 
                                         u'Invalid selection: $cause, $obj', 
                                         cause=error_to_ustr(e), 
                                         obj=pp(input))
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

from copy import deepcopy
def modify(obj, modifier):
    from caty.core.exception import CatyException, throw_caty_exception
    obj = deepcopy(obj)
    if modifier.get('clear', False):
        obj = {}
    s = modifier.get('set', {})
    u = modifier.get('unset', [])
    set_names = set(s.keys())
    unset_names = set(u)
    conflict = set_names.intersection(unset_names)
    if conflict:
        throw_caty_exception(u'SetUnsetConflict', u'$names', names=u', '.join(conflict))
    for k, v in s.items():
        obj[k] = v
    for k in u:
        if k in obj:
            del obj[k]
    return obj

def compose_update(a, b):
    if b.get('clear'):
        return b
    r = {
        u'set': a.get(u'set', {}),
        u'unset': a.get(u'unset', [])[:],
        u'clear': a.get(u'clear', False)
    }
    for k, v in b.get(u'set', {}).items():
        if k in r[u'unset']:
            r[u'unset'].remove(k)
        r[u'set'][k] = v
    r[u'unset'].extend(b.get(u'unset', []))
    return r


