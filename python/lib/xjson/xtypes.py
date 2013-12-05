# coding:utf-8
import decimal
import types
class TaggedValue(object):
    """type tag 付きのスカラー値用のクラス。
    {$tag:foo, $val:1} のようなオブジェクトは、あくまでもスカラー値として扱いたい。
    そのため、タグ付きのデータはすべて {} や dict などではなく
    専用のタグ型によって表現する。
    """
    def __init__(self, t, v):
        self.__tag = t
        self.__value = v

    def set_value(self, v):
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

class _Undefined(object):
    def __nonzero__(self):
        return False

    def __iter__(self):
        return iter([self])

    def __repr__(self):
        return '#undefined'

    def __deepcopy__(self, memo):
        return UNDEFINED

    def __copy__(self):
        return UNDEFINED

class ForeignObject(object):
    def __repr__(self):
        return 'python:<object at ' + hex(id(self)) + '>'

    def __eq__(self, another):
        return isinstance(another, ForeignObject)

    def __ne__(self, another):
        return not isinstance(another, ForeignObject)

UNDEFINED = _Undefined()  # singleton
class Indef(object): pass

INDEF = Indef() # singletone

from UserDict import DictMixin

class OrderedDict(dict, DictMixin):

    def __init__(self, *args, **kwds):
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__end
        except AttributeError:
            self.clear()
        self.update(*args, **kwds)

    def clear(self):
        self.__end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.__map = {}                 # key --> [key, prev, next]
        dict.clear(self)

    def __setitem__(self, key, value):
        if key not in self:
            end = self.__end
            curr = end[1]
            curr[2] = end[1] = self.__map[key] = [key, curr, end]
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        key, prev, next = self.__map.pop(key)
        prev[2] = next
        next[1] = prev

    def __iter__(self):
        end = self.__end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.__end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def popitem(self, last=True):
        if not self:
            raise KeyError('dictionary is empty')
        if last:
            key = reversed(self).next()
        else:
            key = iter(self).next()
        value = self.pop(key)
        return key, value

    def __reduce__(self):
        items = [[k, self[k]] for k in self]
        tmp = self.__map, self.__end
        del self.__map, self.__end
        inst_dict = vars(self).copy()
        self.__map, self.__end = tmp
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def keys(self):
        return list(self)

    setdefault = DictMixin.setdefault
    update = DictMixin.update
    pop = DictMixin.pop
    values = DictMixin.values
    items = DictMixin.items
    iterkeys = DictMixin.iterkeys
    itervalues = DictMixin.itervalues
    iteritems = DictMixin.iteritems

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, self.items())

    def copy(self):
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other

    @property
    def last_key(self):
        return iter(reversed(self)).next()

    @property
    def last_item(self):
        k = self.last_key
        return k, self[k]


_tag_class_dict = {
    int: u'number',
    long: u'number',
    decimal.Decimal: u'number',
    bool: u'boolean',
    dict: u'object',
    unicode: u'string',
    str: u'binary',
    types.NoneType: u'null',
    list: u'array',
    tuple: u'array',
    UNDEFINED.__class__: u'undefined',
    INDEF.__class__: u'indef',
}

_reserved = set(_tag_class_dict.values())
_reserved.add('foreign')
_reserved.add('integer')

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

def tagged(tagname, val=UNDEFINED):
    if tagname in _reserved:
        if not type(val) in _builtin_types[tagname]:
            raise XJSONError(u'$keyword is reserved tag', keyword=tagname)
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
            raise XJSONError(u'No explicit tag')
        t = type(val)
        if t in _tag_class_dict:
            return _tag_class_dict.get(t, u'foreign')
        for k, v in _tag_class_dict.items():
            if isinstance(val, k):
                return v
        return u'foreign'

def untagged(val, explicit=False):
    try:
        return val.value
    except:
        if explicit:
            raise XJSONError('No explicit tag')
        return val

def split_tag(val):
    return tag(val), untagged(val)

def split_exp_tag(val):
    if isinstance(val, TaggedValue):
        return tag(val), untagged(val)
    else:
        return None, val


class XJSONError(Exception):
    def __init__(self, msg, **kwds):
        import string
        Exception.__init__(string.Template(msg).safe_substitute(**kwds))
        self.msg = msg
        self.kwds = kwds
