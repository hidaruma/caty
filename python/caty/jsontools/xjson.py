#coding: utf-8
from caty.util import bind2nd, escape_html
from caty.jsontools import stdjson, decode, encode, CatyEncoder
import caty.jsontools as json
from caty.core.spectypes import INDEF, UNDEFINED
from caty.util.collection import OrderedDict
from topdown import *

import base64
from decimal import Decimal
import xml.dom.minidom as dom
import itertools
from itertools import dropwhile

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
    elif isinstance(o, json.TaggedValue):
        t, v = json.split_tag(o)
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

def series_of_escape(s):
    return len(list(itertools.takewhile(lambda c: c=='\\', reversed(s))))

#@profile
class string(EagerParser):
    def matches(self, seq):
        return seq.current == u'"'

    def __call__(self, seq):
        return _string(seq)

@try_
def _string(seq):
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
    except EndOfBuffer, e:
        raise ParseFailed(seq, u'"')
    else:
        return stdjson.loads(''.join(st))
    finally:
        seq.ignore_hook = False
string = string()

#@profile
class multiline_string(EagerParser):
    def matches(self, seq):
        return seq.rest[0:3] == u"'''"

    def __call__(self, seq):
        try:
            seq.ignore_hook = True
            _ = seq.parse("'''")
            s = seq.parse(until("'''"))
            seq.ignore_hook = False
            _ = seq.parse("'''")
            return stdjson.loads('"%s"' % s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r'))
        finally:
            seq.ignore_hook = False
multiline_string = multiline_string()

_B = set([u't', u'f', u'i'])
#@profile
class boolean(EagerParser):
    def __init__(self, convert=False):
        self.convert = convert

    def matches(self, seq):
        return seq.current and seq.current in _B

    def __call__(self, seq):
        b = seq.parse(['true', 'false', 'indef'])
        if b == 'indef':
            return INDEF
        if self.convert:
            return True if b == 'true' else False
        else:
            return b
boolean = boolean(True)

int_regex = [
                   Regex(r'-?[1-9][0-9]+'),
                   Regex(r'-?[0-9]'),
                 ]
num_regex = [
                   Regex(r'-?[1-9][0-9]+\.[0-9]+([eE][-+]?[0-9]+)?'), 
                   Regex(r'-?[0-9]\.[0-9]+([eE][-+]?[0-9]+)?'), 
                   Regex(r'-?[1-9][0-9]+[eE][-+]?[0-9]+'),
                   Regex(r'-?[0-9][eE][-+]?[0-9]+'),
                   ]

_N = set(u'0123456789-')
#@profile
class number(EagerParser):
    def __init__(self, convert=False):
        self.convert = convert

    def matches(self, seq):
        return seq.current and seq.current in _N

    def __call__(self, seq):
        try:
            n = seq.parse(num_regex)
            if self.convert:
                return Decimal(n)
            else:
                return n
        except:
            i = seq.parse(int_regex)
            if self.convert:
                return int(i)
            else:
                return i
integer = number(True)
number = number(True)

#@profile
class null(EagerParser):
    def __init__(self, convert=False):
        self.convert = convert

    def matches(self, seq):
        return seq.current == u'n'

    def __call__(self, seq):
        n = seq.parse('null')
        if self.convert:
            return None
        else:
            return n
null = null(True)

#@profile
class obj(EagerParser):
    def matches(self, seq):
        return seq.current == u'{'

    def __call__(self, seq):
        seq.parse('{')
        items = seq.parse(option(split(item, u',', True), {}))
        try:
            seq.parse('}')
        except:
            raise ParseError(seq, obj)
        o = {}
        for k ,v in items:
            o[k] = v
        return o
obj = obj()

#@profile
def item(seq):
    k = seq.parse(string)
    seq.parse(':')
    v = eager_choice(*parsers)(seq)
    return k, v

drop_undef = lambda items: reversed(list(dropwhile(lambda x: x is UNDEFINED, reversed(items))))
#@profile
class array(EagerParser):
    def matches(self, seq):
        return seq.current == u'['

    def __call__(self, seq):
        seq.parse('[')
        items = seq.parse(option(split(listitem, u',', True), []))
        actual = list(drop_undef(items))
        try:
            seq.parse(']')
        except:
            raise ParseError(seq, array)
        return actual
array = array()

#@profile
def listitem(seq):
    if seq.current == ']':
        return UNDEFINED
    return eager_choice(*(parsers + [loose_item]))(seq)

#@profile
class loose_item(EagerParser):
    def matches(self, seq):
        return seq.peek(option(u','))

    def __call__(self, seq):
        if not seq.peek(option(u',')):
            raise ParseFailed(seq, array)
        return UNDEFINED
loose_item = loose_item()

class _nothing(object):pass

tag_regex = Regex(r'[-0-9a-zA-Z_]+')
#@profile
class tag(EagerParser):
    def matches(self, seq):
        return seq.current == u'@'

    def __call__(self, seq):
        _ = seq.parse('@')
        name = seq.parse([string, tag_regex])
        value = option(eager_choice(*parsers), _nothing)(seq)
        if value is _nothing:
            return json.TagOnly(name)
        else:
            return json.TaggedValue(name, value)
tag = tag()

ascii = set(list("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!#$%&'()*+,-./:;<=>?@[]^_`{|}~ \t\n\r"))
#@profile
class binary(EagerParser):
    def matches(self, seq):
        return seq.rest[0:2] == u'b"'

    def __call__(self, seq):
        seq.parse('b"')
        end = False
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
                    end = True
                    break
                else:
                    raise ParseError(seq, binary)
            if not end:
                raise ParseError(seq, binary)
            return ''.join(cs)
binary = binary()

class Complex_data(EagerParser):
    def matches(self, seq):
        return seq.current and seq.current in u'@{['

    def __call__(self, seq):
        def push_context(ctx):
            if len(ctx) < 2:
                return
            if isinstance(ctx[-2], json.TaggedValue):
                ctx[-2].set_value(ctx.pop(-1))
            elif isinstance(ctx[-2], OrderedDict):
                k, v = ctx[-2].last_item
                if v != _nothing:
                    raise ParseFailed(seq, u'syntax error')
                a = ctx[-2]
                b = ctx.pop(-1)
                a[k] = b
            else:
                a = ctx[-2]
                b = ctx.pop(-1)
                a.append(b)
        data = None
        context = []
        loose = False
        cont = None
        obj_level = 0
        array_level = 0
        pos = -1
        while not seq.eof:
            if cont:
                if not cont(seq):
                    break
                cont = None
            c = seq.current
            if c in u'@{[':
                choice(list(u'@{['))(seq)
            if c == u'@':
                name = seq.parse([string, tag_regex])
                context.append(json.TaggedValue(name, UNDEFINED))
                loose = False
            elif c == u'{':
                context.append(OrderedDict())
                obj_level += 1
                loose = False
            elif c == u'[':
                context.append([])
                array_level += 1
                loose = True
            if isinstance(context[-1], json.TaggedValue):
                ps = None
                for p in parsers:
                    if p.matches(seq):
                        ps = p
                        break
                if not ps:
                    if context[-1].value is UNDEFINED:
                        context[-1] = json.TagOnly(context[-1].tag)
                    push_context(context)
                    cont = ends
                else:
                    if isinstance(p, Complex_data):
                        continue
                    else:
                        context[-1].set_value(p(seq))
                        push_context(context)
                        cont = ends

            elif isinstance(context[-1], OrderedDict):
                ps = None
                k = seq.parse(option(string))
                if k is None:
                    if seq.parse(option(S(u'}'))):
                        push_context(context)
                        obj_level -= 1
                        cont = ends
                        continue
                    seq.parse(S(u','))
                    if seq.parse(option(S(u'}'))):
                        push_context(context)
                        obj_level -= 1
                        cont = ends
                        continue
                    if not context[-1] or peek(option(S(u',')))(seq):
                        raise ParseFailed(seq, u',')
                    else:
                        k = seq.parse(option(string))
                if k is None:
                    raise ParseFailed(seq, u'syntax error')
                seq.parse(':')
                context[-1][k] = _nothing
                for p in parsers:
                    if p.matches(seq):
                        ps = p
                        break
                if ps is None:
                    raise ParseFailed(seq, u'syntax error')
                else:
                    if isinstance(p, Complex_data):
                        continue
                    else:
                        context[-1][k] = p(seq)
                        if not seq.parse(option(S(u','))):
                            cont = ends
            elif isinstance(context[-1], list):
                ps = None
                for p in parsers:
                    if p.matches(seq):
                        ps = p
                        break
                if ps is None:
                    if option(S(u','))(seq):
                        if loose:
                            context[-1].append(UNDEFINED)
                    elif option(S(u']'))(seq):
                        while context[-1] and context[-1][-1] is UNDEFINED:
                            context[-1].pop(-1)
                        push_context(context)
                        cont = ends
                        array_level -= 1
                        loose = False
                    else:
                        raise ParseFailed(seq, u']')
                else:
                    if isinstance(p, Complex_data):
                        continue
                    else:
                        context[-1].append(p(seq))
                        loose = True
                        seq.parse(option(S(u',')))
            else:
                break
        if obj_level != 0 or array_level != 0:
            raise ParseFailed(seq, u'syntax error')
        assert len(context) == 1, context
        return context[-1]
complex_data = Complex_data()

parsers = [
    number, 
    string, 
    multiline_string, 
    binary,
    boolean, 
    null, 
    complex_data]

def ends(seq):
    return seq.eof or peek(option(choice(u',', u']', u'}')))(seq)

def parse(seq):
    return eager_choice(*parsers)(seq)

def scalar(seq):
    return eager_choice(string, multiline_string, binary, boolean, null, number)(seq)

#@profile
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

