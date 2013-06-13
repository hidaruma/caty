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
import itertools
def reduce_undefined(obj):
    if isinstance(obj, dict):
        r = {}
        for k, v in obj.items():
            if v == UNDEFINED:
                pass
            else:
                r[k] = reduce_undefined(v)
        return r
    elif isinstance(obj, (tuple, list)):
        r = []
        for v in itertools.dropwhile(lambda x:x==UNDEFINED, reversed(obj)):
            r.insert(0, reduce_undefined(v))
        return r
    return obj

class Indef(object): pass

INDEF = Indef

