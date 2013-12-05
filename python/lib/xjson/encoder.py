# coding:utf-8
from xjson.xtypes import *
import decimal
import json
import sys
_is26 = sys.version.startswith('2.6')
class XJSONEncoder(json.encoder.JSONEncoder):
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

    if _is26:
        def _iterencode(self, o, markers=None):
            if isinstance(o, str):
                yield u'b"%s"' % repr(o)[1:-1]
            elif o is INDEF:
                yield u'indef'
            elif o is UNDEFINED:
                pass
            else:
                for v in json.encoder.JSONEncoder._iterencode(self, o, markers):
                    yield v
    else:

        from json.encoder import FLOAT_REPR, INFINITY
        def _floatstr(self, o, allow_nan=None,
                _repr=FLOAT_REPR, _inf=INFINITY, _neginf=-INFINITY):
            # Check for specials.  Note that this type of test is processor
            # and/or platform-specific, so do tests which don't depend on the
            # internals.
            if allow_nan is None:
                allow_nan = self.allow_nan
            if o != o:
                text = 'NaN'
            elif o == _inf:
                text = 'Infinity'
            elif o == _neginf:
                text = '-Infinity'
            else:
                return _repr(o)

            if not allow_nan:
                raise ValueError(
                    "Out of range float values are not JSON compliant: " +
                    repr(o))

            return text

        def iterencode(self, o, _one_shot=False):
            """Encode the given object and yield each string
            representation as available.

            For example::

                for chunk in JSONEncoder().iterencode(bigobject):
                    mysocket.write(chunk)

            """
            from json.encoder import encode_basestring, encode_basestring_ascii
            if self.check_circular:
                markers = {}
            else:
                markers = None
            if self.ensure_ascii:
                _encoder = encode_basestring_ascii
            else:
                _encoder = encode_basestring

            _iterencode = self._make_iterencode(
                markers, self.default, _encoder, self.indent, self._floatstr,
                self.key_separator, self.item_separator, self.sort_keys,
                self.skipkeys, _one_shot, self._iterencode)
            return _iterencode(o, 0)

        def _iterencode(self, o, _current_indent_level, _iterencode_list, _iterencode_dict, markers, _encoder):
            if isinstance(o, unicode):
                yield _encoder(o)
            elif isinstance(o, str):
                yield 'b"%s"' % repr(o)[1:-1]
            elif o is None:
                yield 'null'
            elif o is True:
                yield 'true'
            elif o is False:
                yield 'false'
            elif isinstance(o, (int, long)):
                yield str(o)
            elif isinstance(o, (InternalDecimal, float)):
                yield self._floatstr(o)
            elif isinstance(o, (list, tuple)):
                for chunk in _iterencode_list(o, _current_indent_level):
                    yield chunk
            elif isinstance(o, dict):
                for chunk in _iterencode_dict(o, _current_indent_level):
                    yield chunk
            elif o is UNDEFINED:
                pass
            elif o is INDEF:
                yield u'indef'
            else:
                if markers is not None:
                    markerid = id(o)
                    if markerid in markers:
                        raise ValueError("Circular reference detected")
                    markers[markerid] = o
                o = self.default(o)
                for chunk in self._iterencode(o, _current_indent_level, _iterencode_list, _iterencode_dict, markers, _encoder):
                    yield chunk
                if markers is not None:
                    del markers[markerid]

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

class PPEncoder(XJSONEncoder):
    u"""prettyprint時にタグ型があるとjsonライブラリのdumpsが使えない。
    そのため、タグ型のみをこのクラスでハンドルする必要がある。
    """
    def default(self, o):
        if isinstance(o, TaggedValue):
            return o
        elif isinstance(o, TagOnly):
            return u'@%s' % (o.tag)
        else:
            return XJSONEncoder.default(self, o)
    
    if _is26:
        def _iterencode(self, o, markers=None):
            if isinstance(o, TaggedValue):
                t, v = split_tag(o)
                yield u'@%s ' % t
                for e in self._iterencode(v, markers):
                    yield e
            elif isinstance(o, TagOnly):
                yield u'@%s' % (o.tag)
            elif not isinstance(o, (basestring, bool, int, long, decimal.Decimal, InternalDecimal, dict, list, tuple)) and o is not None:
                if o is UNDEFINED:
                    yield u"#'undefined"
                elif o is _empty:
                    yield u''
                elif o is INDEF:
                    yield u'indef'
                else:
                    yield u'#<foreign %s>' % repr(o)
            else:
                for e in XJSONEncoder._iterencode(self, self._normalize(o), markers):
                    yield e
    else:
        def _iterencode(self, o, _current_indent_level, _iterencode_list, _iterencode_dict, markers, _encoder):
            if isinstance(o, TaggedValue):
                t, v = split_tag(o)
                yield u'@%s ' % t
                for e in self._iterencode(v, _current_indent_level, _iterencode_list, _iterencode_dict, markers, _encoder):
                    yield e
            elif isinstance(o, TagOnly):
                yield u'@%s' % (o.tag)
            elif not isinstance(o, (basestring, long, bool, int, decimal.Decimal, InternalDecimal, dict, list, tuple)) and o is not None:
                if o is UNDEFINED:
                    yield u"#'undefined"
                elif o is _empty:
                    yield u''
                elif o is INDEF:
                    yield u'indef'
                else:
                    yield u'#<foreign %s>' % repr(o)
            else:
                for e in XJSONEncoder._iterencode(self, self._normalize(o), _current_indent_level, _iterencode_list, _iterencode_dict, markers, _encoder):
                    yield e

    def _normalize(self, o):
        if isinstance(o, (tuple, list)):
            return self._erase_undef(o)
        elif isinstance(o, dict):
            return self._reduce_undef(o)
        else:
            return o

    def _erase_undef(self, r):
        import itertools
        l = itertools.dropwhile(lambda x: x==UNDEFINED, reversed(r))
        return [(self._normalize(a) if a is not UNDEFINED else _empty) for a in reversed(list(l))]

    def _reduce_undef(self, o):
        r = {}
        for k, v in o.items():
            if v is UNDEFINED:
                pass
            else:
                r[k] = self._normalize(v)
        return r


def normalize(o):
    if isinstance(o, (tuple, list)):
        return _erase_undef(o)
    elif isinstance(o, dict):
        return _reduce_undef(o)
    else:
        return o


def _erase_undef(r):
    import itertools
    l = itertools.dropwhile(lambda x: x==UNDEFINED, reversed(r))
    return [normalize(a) for a in reversed(list(l))]

def _reduce_undef(o):
    r = {}
    for k, v in o.items():
        if v is UNDEFINED:
            pass
        else:
            r[k] = normalize(v)
    return r

def normalize_number(o):
    if isinstance(o, (tuple, list)):
        return map(normalize_number, o)
    elif isinstance(o, dict):
        return dict([(k, normalize_number(v)) for k, v in o.items()])
    elif isinstance(o, TaggedValue):
        return tagged(o.tag, normalize_number(o.value))
    elif isinstance(o, decimal.Decimal):
        l = long(o)
        if l == o:
            return l
        else:
            return o
    else:
        return o

def encode(obj):
    u"""Caty 内部形式から JSON 標準形式へと変換する。
    """
    if isinstance(obj, TaggedValue):
        return {u'$$tag': obj.tag, u'$$val': encode(obj.value)}
    elif isinstance(obj, TagOnly):
        return {u'$$tag': obj.tag, u'$$no-value': True}
    elif obj is INDEF:
        return {u'$$tag': u'indef', u'$$no-value': True}
    elif isinstance(obj, dict):
        n = {}
        for k, v in obj.items():
            n[k] = encode(v)
        return n
    elif isinstance(obj, (list, tuple)):
        return map(encode, obj)
    else:
        return obj
