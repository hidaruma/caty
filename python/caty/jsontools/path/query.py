# coding: utf-8
from topdown import *
import caty.core.runtimeobject as ro
from caty.jsontools import untagged, tag, tagged, TaggedValue

class JsonQueryError(Exception): pass

class Accessor(object):
    def __init__(self):
        self.error = False

    def find(self, obj):
        raise NotImplementedError

    @property
    def key(self):
        if not self.error:
            return str(self._key())
        else:
            return str('<%s>' % self._key())

    def reset(self):
        self.error = False

    def _key(self):
        raise NotImplementedError

class RootAccessor(Accessor):
    def find(self, obj):
        yield obj

    def _key(self):
        return '$'

class NameAccessor(Accessor):
    def __init__(self, name):
        Accessor.__init__(self)
        self._name = name

    def find(self, obj, ignored=False):
        if isinstance(obj, TaggedValue) and not ignored:
            yield self.find(untagged(obj), True).next()
        else:
            yield obj[self._name]

    def _key(self):
        return self._name if not ' ' in self._name else '"%s"' % self._name

class IndexAccessor(NameAccessor):
    def find(self, obj):
        if isinstance(obj, TaggedValue) and not ignored:
            yield self.find(untagged(obj), True).next()
        else:
            yield obj[int(self._name)]

class WildcardNameAccesor(Accessor):
    def find(self, obj):
        if not hasattr(obj, 'values'):
            for v in obj.values():
                yield v
        else:
            raise JsonQueryError(ro.i18n.get(u'Not a $type: $obj', type=u'object', obj=str(obj)))

    def _key(self):
        return '*'

class WildcardIndexAccesor(Accessor):
    def find(self, obj):
        if isinstance(obj, (list, tuple)):
            for v in obj:
                yield v
        else:
            raise JsonQueryError(ro.i18n.get(u'Not a $type: $obj', type=u'array', obj=str(obj)))

    def _key(self):
        return '#'

class TagAccessor(Accessor):
    def find(self, obj):
        yield tag(obj)

    def _key(self):
        return 'tag()'

class ExpTagAccessor(Accessor):
    def find(self, obj):
        yield tag(obj, True)

    def _key(self):
        return 'exp-tag()'

class TagContentAccessor(Accessor):
    def find(self, obj):
        yield untagged(obj)

    def _key(self):
        return 'untagged()'

class LengthAccessor(Accessor):
    def find(self, obj):
        if isinstance(obj, (list, tuple)):
            yield len(obj)
        else:
            raise JsonQueryError(ro.i18n.get(u'Not a $type: $obj', type=u'array', obj=str(obj)))

    def _key(self):
        return 'length()'

class AccessorPair(Accessor):
    def __init__(self, a, b):
        self._prev = a
        self._next = b

    def find(self, obj):
        for j in self._prev.find(obj):
            try:
                for o in self._next.find(j):
                    yield o
            except:
                self._next.error = True
                raise
    
    def error():
        def get(self):
            return self._next.error

        def set(self, value):
            self._next.error = value

        return get, set
    error = property(*error())

    def reset(self):
        self._next.reset()

    def key(self):
        return '%s.%s' % (self._prev.key, self._next.key)

@as_parser
def query(seq):
    qs = accessor(seq)
    return reduce(lambda a, b: AccessorPair(a, b), qs)

def accessor(seq):
    r = root(seq)
    _ = seq.parse(option('.'))
    if _:
        tokens = split([tag_, exp_tag, untagged_, length, number, name, quoted_name, o_wild, i_wild], '.')(seq)
        return [r] + tokens
    else:
        return [r]

def root(seq):
    _ = seq.parse('$')
    return RootAccessor()

def name(seq):
    n = seq.parse(Regex(r'[^ "#*.]+'))
    return NameAccessor(n)

def quoted_name(seq):
    _ = seq.parse('"')
    s = seq.parse(until('"'))
    _ = seq.parse('"')
    return NameAccessor(s)

def number(seq):
    n = seq.parse(Regex(r'[0-9]+'))
    return IndexAccessor(n)

def o_wild(seq):
    _ = seq.parse('*')
    return WildcardNameAccesor()

def i_wild(seq):
    _ = seq.parse('#')
    return WildcardIndexAccesor()

def tag_(seq):
    seq.parse('tag()')
    return TagAccessor()

def exp_tag(seq):
    seq.parse('exp-tag()')
    return ExpTagAccessor()

def untagged_(seq):
    seq.parse(choice('untagged()', 'content()'))
    return TagContentAccessor()

def length(seq):
    seq.parse('length()')
    return LengthAccessor()

