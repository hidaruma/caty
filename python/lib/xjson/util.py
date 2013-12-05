# coding: utf-8
from xjson.xtypes import *


import base64
from decimal import Decimal
import xml.dom.minidom as dom

def toxml(o):
    doc = dom.Document()
    _toxml(o, doc, doc)
    r = doc.toxml()
    if not isinstance(r, unicode):
        return unicode(r)
    else:
        return r

def _toxml(o, p, doc):
    if o is True:    
        e = doc.createElement('true')
        p.appendChild(e)
    elif o is False:    
        e = doc.createElement('false')
        p.appendChild(e)
    elif isinstance(o, (int, long, Decimal)):
        e = doc.createElement('number')
        t = doc.createTextNode(unicode(str(o)))
        e.appendChild(t)
        p.appendChild(e)
    elif isinstance(o, unicode):
        e = doc.createElement('string')
        t = doc.createTextNode(o)
        e.appendChild(t)
        p.appendChild(e)
    elif isinstance(o, str):
        e = doc.createElement('binary')
        t = doc.createTextNode(unicode(str(base64.b64encode(o))))
        e.appendChild(t)
        p.appendChild(e)
    elif isinstance(o, list):
        e = doc.createElement('array')
        for i in o:
            _toxml(i, e, doc)
        p.appendChild(e)
    elif isinstance(o, dict):
        e = doc.createElement('object')
        for k, v in o.items():
            pr = doc.createElement('property')
            pr.setAttribute('name', k)
            _toxml(v, pr, doc)
            e.appendChild(pr)
        p.appendChild(e)
    elif isinstance(o, TaggedValue):
        t, v = split_tag(o)
        tn = doc.createElement('tagged')
        tn.setAttribute('tag', t)
        _toxml(v, tn, doc)
        p.appendChild(tn)
    elif o is INDEF:
        e = doc.createElement('indef')
        p.appendChild(e)
    elif o is None:    
        e = doc.createElement('null')
        p.appendChild(e)

def load(fo):
    s = fo.read()
    return loads(s)

def loads(s):
    from xjson.parser import CharSeq, remove_comment, parsers
    cs = CharSeq(s, hook=remove_comment, auto_remove_ws=True)
    r = cs.parse(parsers)
    if not cs.eof:
        raise Exception('Line No %d: %s' % (cs.line, cs.rest))
    return r

def dumps(obj):
    return xjson.pp(obj)

def dump(obj, fo):
    fo.write(dumps(obj))

def load_from_json(fo):
    return decode(json.load(fo))

def loads_from_json(s):
    return decode(json.loads(s))

def dump_to_json(obj, fo, **kwds):
    return json.dump(encode(obj), fo, **kwds)

def dumps_to_json(obj, **kwds):
    return json.dumps(encode(obj), **kwds)

def obj2path(obj):
    u"""辞書形式の JSON オブジェクトをパス形式に変換する。
    パス形式の JSON は深さが 1 の辞書となり、
    入れ子関係はすべてフラットにされてキーの値がパス情報となる。
    すなわち以下のオブジェクトは

    {
        "a": 1,
        "b": {
            "c": 2
        }
    }

    このような形式に変換される。

    {
        "a": 1,
        "b.c": 2
    }
    """
    assert isinstance(obj, dict), obj
    def flatten(obj, parent='$'):
        if isinstance(obj, dict):
            n = 0
            for k, v in obj.items():
                n += 1
                for r in flatten(v, parent + '.' + k):
                    yield r
            if n == 0: # 空のオブジェクト
                yield parent + '.' + '{}', None
        elif isinstance(obj, (list, tuple)):
            n = 0
            for i, v in enumerate(obj):
                n += 1
                for r in flatten(v, parent + '.' + str(i)):
                    yield r
            if n == 0:# 空のリスト
                yield parent + '.' + '[]', None
        else:
            yield parent, obj
    p = {}
    p.update(list(flatten(obj)))
    return p

import types
def is_json(obj):
    if isinstance(obj, (long, int, Decimal, unicode, str, bool, types.NoneType)):
        return True
    elif isinstance(obj, dict):
        return all(map(is_json, obj.values()))
    elif isinstance(obj, list):
        return all(map(is_json, obj))
    else:
        return False


def prettyprint(obj, depth=0, encoding=None):
    from xjson.encoder import PPEncoder
    import json
    v = json.dumps(obj, cls=PPEncoder, indent=4, ensure_ascii=False)
    if isinstance(v, unicode):
        return v
    else:
        return unicode(str(v))

pp = prettyprint

