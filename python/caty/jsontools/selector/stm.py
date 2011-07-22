#coding: utf-8
from caty.jsontools import untagged, tag, tagged, TaggedValue
class Nothing(object):
    u"""{} | xjson:select $.aなど、該当プロパティのない非strictアクセス時に返すオブジェクト
    """
    def __init__(self):
        self.__iterated = False

    def __iter__(self):
        return Nothing()

    def next(self):
        if not self.__iterated:
            self.__iterated = True
            return self
        else:
            raise StopIteration()
            
class Selector(object):
    def __init__(self):
        self.next = None
        self.empty_when_error = False

    def chain(self, next):
        if not self.next:
            self.next = next
            self.next.empty_when_error = self.empty_when_error
        else:
            self.next.chain(next)
        return self

    def select(self, obj):
        o = self.run(obj)
        if self.next:
            for v in o:
                for x in self.next.select(v):
                    if not isinstance(x, Nothing):
                        yield x
        else:
            for v in o:
                if not isinstance(v, Nothing):
                    yield v

    def run(self, obj):
        raise NotImplementedError()

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

class PropertySelector(Selector):
    def __init__(self, prop):
        Selector.__init__(self)
        self.property = prop

    def run(self, obj, ignored=False):
        if isinstance(obj, dict):
            if self.property in obj:
                yield obj[self.property]
            elif not self.empty_when_error:
                raise KeyError(self.property)
            else:
                yield Nothing()
        elif isinstance(obj, Nothing):
            yield Nothing()
        elif isinstance(obj, TaggedValue) and not ignored:
            for x in self.run(untagged(obj), True):
                yield x
        else:
            #if not self.empty_when_error:
            raise Exception('not a object')

    def replace(self, obj, new, allow_loose):
        if self.next:
            obj[self.property] = self.next.replace(obj[self.property], new, allow_loose)
        else:
            obj[self.property] = new
            return obj

class ItemSelector(Selector):
    def __init__(self, prop):
        Selector.__init__(self)
        self.property = prop

    def run(self, obj, ignored=False):
        if isinstance(obj, (list, tuple)):
            if len(obj) > self.property:
                yield obj[self.property]
            else:
                if self.empty_when_error:
                    yield Nothing()
                else:
                    raise IndexError(str(self.property))
        elif isinstance(obj, Nothing):
            yield Nothing()
        elif isinstance(obj, TaggedValue) and not ignored:
            for x in self.run(untagged(obj), True):
                yield x
        else:
            if not self.empty_when_error:
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

class NameWildcardSelector(Selector):
    def run(self, obj):
        if isinstance(obj, dict):
            for v in obj.values():
                yield v
        elif isinstance(obj, Nothing):
            yield Nothing()
        elif isinstance(obj, TaggedValue):
            for x in self.run(untagged(obj)):
                yield x
        else:
            raise Exception('not a object')

    def replace(self, obj, new, allow_loose):
        for k in obj.keys():
            obj[k] = new

class ItemWildcardSelector(Selector):
    def run(self, obj):
        if isinstance(obj, (tuple, list)):
            for v in obj:
                yield v
        elif isinstance(obj, Nothing):
            yield Nothing()
        elif isinstance(obj, TaggedValue):
            for x in self.run(untagged(obj)):
                yield x
        else:
            raise Exception('not a array')

    def replace(self, obj, new, allow_loose):
        for k in obj.keys():
            obj[k] = new

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

class TagReplacer(Selector):
    def __init__(self, name, explicit):
        Selector.__init__(self)
        self.name = name
        self.explicit = explicit

    def replace(self, obj, new, allow_loose):
        return tagged(new, obj, self.explicit)


