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

from xjson.xtypes import _Undefined, UNDEFINED, Indef, INDEF, ForeignObject

