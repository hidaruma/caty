# coding: utf-8
from xjson.xtypes import *

def decode(obj):
    u"""標準の JSON 形式から Caty 内部形式へと変換する。
    内部形式ではタグの扱いが異なる。
    """
    if isinstance(obj, dict):
        if u'$$tag' in obj:
            if u'$$val' in obj:
                return TaggedValue(obj[u'$$tag'], decode(obj[u'$$val']))
            elif u'$$no-value' in obj:
                if obj[u'$$tag'] == u'indef':
                    return INDEF
                return TagOnly(obj[u'$$tag'])
            else:
                raise XJSONError(u'No $$val or $$no-value that matches to $$tag')
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
