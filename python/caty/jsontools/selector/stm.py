#coding: utf-8
from caty.jsontools import untagged, tag, tagged, TaggedValue
from caty import UNDEFINED

class Nothing(Exception):
    u"""未定義値の検出時に発生する例外
    """

class Selector(object):
    def __init__(self):
        self.next = None
        self.is_optional = False

    def chain(self, next):
        if not self.next:
            self.next = next
            if not self.next.is_optional:
                self.next.is_optional = self.is_optional
            else:
                self.is_optional = self.next.is_optional
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
            obj[self.property] = self.next.replace(obj[self.property], new, allow_loose)
        else:
            obj[self.property] = new
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
        if self.next:
            obj[self.property] = self.next.replace(obj[self.property], new, allow_loose)
        else:
            if self.property < len(obj):
                obj[self.property] = new
                return obj
            elif self.property == len(obj):
                obj.append(new)
                return obj
            else:
                if allow_loose:
                    while len(obj) < self.property:
                        obj.append(caty.UNDEFINED)
                    obj.append(new)
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

