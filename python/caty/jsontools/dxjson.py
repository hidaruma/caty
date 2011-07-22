#coding: utf-8
from topdown import *
from caty.core.casm.language.util import docstring, remove_comment
from caty.jsontools import TaggedValue
from caty.util import bind2nd
import caty.jsontools.stdjson as stdjson
def _is_doc_str(seq):
    _ = seq.parse(option(docstring))
    if _:
        try:
            seq.parse(skip_ws)
            seq.parse(['"', "'''"] + list('1234567890ft-[{'))
            return True
        except:
            return False
    return False

remove_comment = bind2nd(remove_comment, _is_doc_str)

def load(f):
    return loads(f.read())

def loads(s):
    cs = CharSeq(s, hook=remove_comment, auto_remove_ws=True)
    r = cs.parse(parsers)
    if not cs.eof:
        raise Exception(cs.text)
    return r

def doc_node(d, n):
    if isinstance(n ,TaggedValue) and n.tag in ('_doc', '_value', '_section', '_list'):
        v = {'doc': d, 'value': n}
    else:
        v = {'doc': d, 'value': TaggedValue(u'_value', n)}
    return TaggedValue(u'_doc', v)

def section(d, n):
    return TaggedValue(u'_section', n)

def listing(d, n):
    return TaggedValue(u'_list', n)

@try_
def string(seq):
    def series_of_escape(s):
        import itertools
        return len(list(itertools.takewhile(lambda c: c=='\\', reversed(s))))
    try:
        d = seq.parse(option(docstring))
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
        return doc_node(d, stdjson.loads(''.join(st)))
    except EndOfBuffer, e:
        raise ParseFailed(seq, string)
    finally:
        seq.ignore_hook = False

def multiline_string(seq):
    try:
        seq.ignore_hook = True
        d = seq.parse(option(docstring))
        _ = seq.parse("'''")
        s = seq.parse(until("'''"))
        seq.ignore_hook = False
        _ = seq.parse("'''")
        return doc_node(d, stdjson.loads('"%s"' % s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')))
    finally:
        seq.ignore_hook = False

def boolean(seq, convert=False):
    d = seq.parse(option(docstring))
    b = seq.parse(['true', 'false'])
    if convert:
        return doc_node(d, True if b == 'true' else False)
    else:
        return doc_node(b, b)

def integer(seq, convert=False):
    d = seq.parse(option(docstring))
    i = seq.parse([
                   Regex(r'-?[1-9][0-9]+'),
                   Regex(r'-?[0-9]'),
                 ])
    if convert:
        return doc_node(d, int(i))
    else:
        return doc_node(d, i)

def number(seq, convert=False):
    d = seq.parse(option(docstring))
    n = seq.parse([
                   Regex(r'-?[1-9][0-9]+\.[0-9]+([eE][-+]?[0-9]+)?'), 
                   Regex(r'-?[0-9]\.[0-9]+([eE][-+]?[0-9]+)?'), 
                   Regex(r'-?[1-9][0-9]+[eE][-+]?[0-9]+'),
                   Regex(r'-?[0-9][eE][-+]?[0-9]+'),
                   ])
    if convert:
        return doc_node(d, Decimal(n))
    else:
        return doc_node(d, n)

def null(seq, convert=False):
    d = seq.parse(option(docstring))
    n = seq.parse('null')
    if convert:
        return doc_node(d, None)
    else:
        return doc_node(d, n)

def comma(seq):
    o = seq.ignore_hook
    try:
        seq.ignore_hook = True
        seq.parse(',')
        seq.parse(skip_ws)
        ds = seq.parse(option(inline_doc_string))
        return ds
    finally:
        seq.ignore_hook = o

def obj(seq):
    d = seq.parse(option(docstring))
    seq.parse('{')
    items = seq.parse(option(split(item, comma, True), {}))
    seq.parse('}')
    o = {}
    for k, v in items:
        o[k] = v
    return section(d, o)

def item(seq):
    d = seq.parse(option(docstring))
    k = seq.parse(string).value['value'].value
    seq.parse(':')
    v = seq.parse(parsers)
    return k, doc_node(d, v)

def array(seq):
    d = seq.parse(option(docstring))
    seq.parse('[')
    items = seq.parse(option(split(a_item, comma, True), []))
    seq.parse(']')
    return listing(d, [i[1] for i in items])

def a_item(seq):
    d = seq.parse(option(docstring))
    v = doc_node(None, seq.parse(parsers))
    if d:
        v.value['value'].value['doc'] = d
    return None, v

def tag(seq):
    d = seq.parse(option(docstring))
    _ = seq.parse('@')
    name = seq.parse([string, Regex(r'[-0-9a-zA-Z_]+')])
    value = seq.parse(parsers)
    return doc_node(d, TaggedValue(name, value))

def inline_doc_string(seq):
    seq.parse('//**')
    c = seq.parse(until('\n'))
    seq.parse('\n')
    return c.strip().lstrip('*')

parsers = [
    tag,
    bind2nd(number, True), 
    bind2nd(integer, True), 
    string, 
    multiline_string, 
    bind2nd(boolean, True), 
    bind2nd(null, True), 
    array, 
    obj]

class split(Parser):
    def __init__(self, parser, delim, allow_last_delim=False):
        self.parser = parser
        self.delim = delim
        self.allow_last_delim = allow_last_delim

    def __call__(self, seq):
        r = []
        r.append(seq.parse(self.parser))
        if seq.eof:
            return r
        while True:
            try:
                a = seq.parse(self.delim)
                if a:
                    r[-1][1].value['value'].value['doc'] = a
            except EndOfBuffer, e:
                raise
            except ParseFailed, e:
                break
            try:
                b = seq.parse(self.parser)
            except EndOfBuffer, e:
                raise
            except ParseFailed, e:
                if self.allow_last_delim:
                    break
                else:
                    raise
            else:
                r.append(b)
                if seq.eof:
                    break
        return r


