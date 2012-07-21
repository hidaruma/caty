#coding: utf-8
import base64
from decimal import Decimal
import xml.dom.minidom as dom
from topdown import *
import caty.jsontools as json
from caty.util import bind2nd, escape_html
from caty.jsontools import stdjson, decode, encode, CatyEncoder

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
    elif isinstance(o, (int, Decimal)):
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
    elif isinstance(o, json.TaggedValue):
        t, v = json.split_tag(o)
        tn = doc.createElement('tagged')
        tn.setAttribute('tag', t)
        _toxml(v, tn, doc)
        p.appendChild(tn)
    elif o is None:    
        e = doc.createElement('null')
        p.appendChild(e)


def load(fo):
    s = fo.read()
    return loads(s)

def loads(s):
    cs = CharSeq(s, hook=remove_comment, auto_remove_ws=True)
    r = cs.parse(parsers)
    if not cs.eof:
        raise Exception('Line No %d: %s' % (cs.line, cs.rest))
    return r

def dumps(obj):
    return json.pp(obj)

def dump(obj, fo):
    fo.write(dumps(obj))

def load_from_json(fo):
    return decode(stdjson.load(fo))

def loads_from_json(s):
    return decode(stdjson.loads(s))

def dump_to_json(obj, fo, **kwds):
    return stdjson.dump(encode(obj), fo, **kwds)

def dumps_to_json(obj, **kwds):
    return stdjson.dumps(encode(obj), **kwds)

@try_
def string(seq):
    def series_of_escape(s):
        import itertools
        return len(list(itertools.takewhile(lambda c: c=='\\', reversed(s))))
    try:
        seq.ignore_hook = True
        st = [seq.parse('"')]
        s = seq.parse(until('"'))
        while True:
            if series_of_escape(s) % 2 == 0:
                st.append(s)
                break
            else:
                st.append(s)
                s = seq.parse(Regex(r'"[^"]*'))
        st.append(seq.parse('"'))
        return stdjson.loads(''.join(st))
    except EndOfBuffer, e:
        raise ParseFailed(seq, string)
    finally:
        seq.ignore_hook = False

def multiline_string(seq):
    try:
        seq.ignore_hook = True
        _ = seq.parse("'''")
        s = seq.parse(until("'''"))
        seq.ignore_hook = False
        _ = seq.parse("'''")
        return stdjson.loads('"%s"' % s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r'))
    finally:
        seq.ignore_hook = False

def boolean(seq, convert=False):
    b = seq.parse(['true', 'false'])
    if convert:
        return True if b == 'true' else False
    else:
        return b

def integer(seq, convert=False):
    i = seq.parse([
                   Regex(r'-?[1-9][0-9]+'),
                   Regex(r'-?[0-9]'),
                 ])
    if convert:
        return int(i)
    else:
        return i

def number(seq, convert=False):
    n = seq.parse([
                   Regex(r'-?[1-9][0-9]+\.[0-9]+([eE][-+]?[0-9]+)?'), 
                   Regex(r'-?[0-9]\.[0-9]+([eE][-+]?[0-9]+)?'), 
                   Regex(r'-?[1-9][0-9]+[eE][-+]?[0-9]+'),
                   Regex(r'-?[0-9][eE][-+]?[0-9]+'),
                   ])
    if convert:
        return Decimal(n)
    else:
        return n

def null(seq, convert=False):
    n = seq.parse('null')
    if convert:
        return None
    else:
        return n

def comma(seq):
    return seq.parse(',')

def obj(seq):
    seq.parse('{')
    items = seq.parse(option(split(item, comma, True), {}))
    try:
        seq.parse('}')
    except:
        raise ParseError(seq, obj)
    o = {}
    for k ,v in items:
        o[k] = v
    return o

def item(seq):
    k = seq.parse(string)
    seq.parse(':')
    v = seq.parse(parsers)
    return k, v

def array(seq):
    from caty import UNDEFINED
    from itertools import dropwhile
    seq.parse('[')
    items = seq.parse(option(split(listitem, comma, True), []))
    actual = list(reversed(list(dropwhile(lambda x: x is UNDEFINED, reversed(items)))))
    try:
        seq.parse(']')
    except:
        raise ParseError(seq, array)
    return actual

def listitem(seq):
    from caty import UNDEFINED
    if seq.current == ']':
        return UNDEFINED
    return seq.parse([parsers, loose_item])

def loose_item(seq):
    from caty import UNDEFINED
    if not seq.peek(option(comma)):
        raise ParseFailed(seq, array)
    return UNDEFINED

class _nothing(object):pass

def tag(seq):
    _ = seq.parse('@')
    name = seq.parse([string, Regex(r'[-0-9a-zA-Z_]+')])
    value = seq.parse(option(parsers, _nothing))
    if value is _nothing:
        return json.TagOnly(name)
    else:
        return json.TaggedValue(name, value)

ascii = set(list("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!#$%&'()*+,-./:;<=>?@[]^_`{|}~ \t\n\r"))
def binary(seq):
    seq.parse('b"')
    with strict():
        cs = []
        while not seq.eof:
            if seq.current in ascii:
                cs.append(str(seq.current))
                seq.next()
            elif seq.current == '\\':
                seq.next()
                c = choice('x', '"', '\\')(seq)
                if c != 'x':
                    cs.append(c)
                else:
                    a = seq.current
                    seq.next()
                    b = seq.current
                    seq.next()
                    cs.append(chr(int(a+b, 16)))
            elif seq.current == '"':
                seq.next()
                break
            else:
                raise ParseError(seq, binary)
        return ''.join(cs)

parsers = [
    tag,
    bind2nd(number, True), 
    bind2nd(integer, True), 
    string, 
    multiline_string, 
    binary,
    bind2nd(boolean, True), 
    bind2nd(null, True), 
    array, 
    obj]

def parse(seq):
    return seq.parse(parsers)

def remove_comment(seq):
    seq.parse(skip_ws)
    while not seq.eof and seq.current == '/':
        s = seq.parse(option(['//', '/*{{{', '/*']))
        if s == '//':
            seq.parse([until('\n'), until('\r')])
            seq.parse(skip_ws)
        elif s == '/*{{{':
            c = seq.parse(until('}}}*/'))
            seq.parse('}}}*/')
            seq.parse(skip_ws)
        elif s == '/*':
            c = seq.parse(until('*/'))
            seq.parse('*/')
            seq.parse(skip_ws)
        else:
            break

def singleline_comment(seq):
    if seq.parse(option('//', None)) == None: return
    seq.parse([until('\n'), until('\r')])

def multiline_comment(seq):
    if seq.parse(option('/*', None)) == None: return
    seq.parse(until('*/'))
    seq.parse('*/')

