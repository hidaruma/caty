#coding: utf-8
from caty.jsontools import untagged, tag, tagged, TaggedValue, split_tag, xjson
from caty import UNDEFINED

class Nothing(Exception):
    u"""未定義値の検出時に発生する例外
    """

class Selector(object):
    def __init__(self):
        self.next = None
        self.is_optional = False

    def set_optional(self, o):
        self.is_optional = o
        if self.next:
            self.next.set_optional(o)

    def chain(self, next):
        if not self.next:
            self.next = next
        else:
            self.next.chain(next)
        return self

    def select(self, obj):
        o = self.run(obj)
        if self.next:
            for v in o:
                for x in self.next.select(v):
                    if x is UNDEFINED and not self.is_optional:
                        raise Nothing()
                    else:
                        yield x
        else:
            for v in o:
                if v is UNDEFINED and not self.is_optional:
                    raise Nothing()
                else:
                    yield v

    def run(self, obj):
        raise NotImplementedError()

    def _to_str(self):
        return u''

    def to_str(self):
        r = self._to_str()
        if self.next:
            r = '%s.%s' % (r, self.next.to_str())
        return r

class SelectorWrapper(object):
    def __init__(self, selector):
        self.selector = selector
        self.default = UNDEFINED

    def set_optional(self, o):
        self.selector.set_optional(o)

    def set_default(self, default):
        self.default = default

    def select(self, obj):
        for r in self.selector.select(obj):
            if r is UNDEFINED and self.default is not UNDEFINED:
                yield self.default
            else:
                yield r

    def replace(self, src, new, allow_loose=False):
        return self.selector.replace(src, new, allow_loose)

    def to_str(self):
        return self._to_str()

    def _to_str(self):
        r = self.selector.to_str()
        if self.selector.is_optional:
            r += u'?'
        if self.default is not UNDEFINED:
            r += xjson.dumps(self.default)
        return r


class AllSelector(Selector):
    def run(self, obj):
        yield obj

    def replace(self, src, new, allow_loose=False):
        if self.next:
            r = self.next.replace(src, new, allow_loose)
            if not r:
                return src
            else:
                return r
        else:
            return new

    def _to_str(self):
        return '$'

class PropertySelector(Selector):
    def __init__(self, prop, opt=False):
        Selector.__init__(self)
        self.property = prop
        self.is_optional = opt

    def run(self, obj, ignored=False):
        if isinstance(obj, dict):
            if self.property in obj:
                yield obj[self.property]
            elif self.is_optional:
                yield UNDEFINED
            else:
                raise KeyError(self.property)
        elif obj is UNDEFINED:
            yield UNDEFINED
        elif isinstance(obj, TaggedValue) and not ignored:
            for x in self.run(untagged(obj), True):
                yield x
        else:
            #if not self.is_optional:
            raise Exception('not a object')

    def replace(self, obj, new, allow_loose):
        if self.next:
            untagged(obj)[self.property] = self.next.replace(untagged(obj)[self.property], new, allow_loose)
        else:
            untagged(obj)[self.property] = new
            return obj

    def _to_str(self):
        return self.property if ' ' not in self.property else '"%s"' % self.property

class ItemSelector(Selector):
    def __init__(self, prop, optional=False):
        Selector.__init__(self)
        self.property = prop
        self.is_optional = optional

    def run(self, obj, ignored=False):
        if isinstance(obj, (list, tuple)):
            if len(obj) > self.property:
                yield obj[self.property]
            else:
                if self.is_optional:
                    yield UNDEFINED
                else:
                    raise IndexError(str(self.property))
        elif obj is UNDEFINED:
            yield UNDEFINED
        elif isinstance(obj, TaggedValue) and not ignored:
            for x in self.run(untagged(obj), True):
                yield x
        else:
            if not self.is_optional:
                raise Exception('not a array')

    def replace(self, obj, new, allow_loose):
        import caty
        if isinstance(obj, TaggedValue):
            tgt = untagged(obj)
        else:
            tgt = obj
        if self.next:
            tgt[self.property] = self.next.replace(tgt[self.property], new, allow_loose)
        else:
            if self.property < len(tgt):
                tgt[self.property] = new
                return obj
            elif self.property == len(tgt):
                tgt.append(new)
                return obj
            else:
                if allow_loose:
                    while len(tgt) < self.property:
                        tgt.append(caty.UNDEFINED)
                    tgt.append(new)
                    return obj
                else:
                    raise IndexError(self.property)

    def _to_str(self):
        return str(self.property)

class NameWildcardSelector(Selector):
    def run(self, obj):
        if isinstance(obj, dict):
            for v in obj.values():
                yield v
        elif obj is UNDEFINED:
            yield UNDEFINED
        elif isinstance(obj, TaggedValue):
            for x in self.run(untagged(obj)):
                yield x
        else:
            raise Exception('not a object')

    def replace(self, obj, new, allow_loose):
        for k in obj.keys():
            obj[k] = new

    def _to_str(self):
        return '*'

class ItemWildcardSelector(Selector):
    def run(self, obj):
        if isinstance(obj, (tuple, list)):
            for v in obj:
                yield v
        elif obj is UNDEFINED:
            yield UNDEFINED
        elif isinstance(obj, TaggedValue):
            for x in self.run(untagged(obj)):
                yield x
        else:
            raise Exception('not a array')

    def replace(self, obj, new, allow_loose):
        for k in obj.keys():
            obj[k] = new

    def _to_str(self):
        return '#'

class TagSelector(Selector):
    def __init__(self, name, explicit):
        Selector.__init__(self)
        self.name = name
        self.explicit = explicit

    def run(self, obj):
        v = untagged(obj, self.explicit)
        if self.name:
            if self.name != tag(obj):
                raise Exception('%s!=%s' % (self.name, tag(obj)))
        yield v

    def _to_str(self):
        r = '^%s*' % self.name
        if self.explicit:
            r += '!'
        return r

class TagReplacer(Selector):
    def __init__(self, name, explicit):
        Selector.__init__(self)
        self.name = name
        self.explicit = explicit

    def replace(self, obj, new, allow_loose):
        return tagged(new, obj, self.explicit)

    def _to_str(self):
        r = '^%s^' % self.name
        if self.explicit:
            r += '!'
        return r


class TagNameSelector(Selector):
    def __init__(self, explicit):
        Selector.__init__(self)
        self.explicit = explicit

    def run(self, obj):
        v = tag(obj, self.explicit)
        yield v

    def _to_str(self):
        if self.explicit:
            return 'exp-tag()'
        else:
            return 'tag()'

class TagContentSelector(Selector):
    def __init__(self, src):
        Selector.__init__(self)
        self.src= src

    def run(self, obj):
        v = untagged(obj)
        yield v


    def replace(self, obj, new, allow_loose):
        t, v = split_tag(obj)
        if self.next:
            return tagged(t, self.next.replace(v, new, allow_loose))
        else:
            assert False

    def _to_str(self):
        return self.src

class LengthSelector(Selector):

    def __init__(self):
        Selector.__init__(self)

    def run(self, obj, ignored=False):
        if isinstance(obj, (list, tuple)):
            yield len(obj)
        else:
            raise Exception('not a array')

    def _to_str(self):
        return 'length()'

