# coding:utf-8
from topdown import *
from decimal import Decimal
import re

#__all__ = ['annotation', 'name', 'comma', 'chain_flat', 'docstring', 'SchemaSyntaxError', 'remove_comment']

def name(seq):
    return seq.parse(Regex(r'(([a-zA-Z_][-a-zA-Z0-9_]*)|(\$))'))

def comma(seq):
    _ = seq.parse(',')
    return _

class chain_flat(Parser):
    def __init__(self, parser, op):
        self.parser = parser
        self.op = op

    def __call__(self, seq):
        r = []
        r.append(seq.parse(self.parser))
        while True:
            try:
                a = seq.parse(self.op)
            except ParseFailed, e:
                break
            else:
                #カンマへの対応のみなので、 op の結果は捨てる
                try:
                    b = seq.parse(self.parser)
                    r.append(b)
                except ParseFailed:
                    break
        return r

def docstring(seq):
    return many1(__docstring)(seq)[-1]

def __docstring(seq):
    seq.parse(skip_ws)
    seq.parse('/**')
    doc = seq.parse(until('*/')).strip('\n')#Regex(r'/\*\*.+?\*/', re.S))[3:-2].strip('\n')
    seq.parse('*/')
    seq.parse(skip_ws)
    r = []
    lines = [d.strip() for d in doc.splitlines()]
    space = 0
    if not lines:
        return u''
    for i in list(lines[0]):
        if i == ' ':
            space += 1
        else:
            break
    d = []
    for l in lines:
        l = l.replace(' '*space, '', 1)
        if l == '*':
            l = ''
        elif l.startswith('* '):
            l = l[2:]
        d.append(l)
    return u'\n'.join(d)

class SchemaSyntaxError(Exception):
    def __init__(self, exception):
        self.exception = exception

    def __str__(self):
        return str(self.exception)

    def __unicode__(self):
        return unicode(self.exception)

    def __repr__(self):
        return repr(self.exception)

def value(seq):
    return seq.parse([string, boolean, number, integer])

def boolean(seq):
    b = seq.parse(['true', 'false'])
    if b == 'true':
        return True
    else:
        return False

def integer(seq):
    return int(seq.parse(Regex(r'-?[0-9]+')))

def number(seq):
    return Decimal(seq.parse(Regex(r'-?[0-9]+\.[0-9]+')))

from caty.jsontools.xjson import parsers, string



def _is_doc_str(seq):
    _ = seq.parse(option(docstring))
    #return bool(_)
    if _:
        try:
            seq.parse(skip_ws)
            _comment(seq, None)
            seq.parse(skip_ws)
            return False
        except:
            return True
    return False

def _item(seq):
    def _annotation(seq):
        seq.parse('@')
        seq.parse('[')
        seq.parse(until(']'))
        seq.parse(']')
    seq.parse(option(_annotation))
    seq.parse(skip_ws)
    seq.parse([string, '*'])
    seq.parse(skip_ws)
    seq.parse(':')

from caty.util import bind2nd
def remove_comment(seq, doc_str_checker=_is_doc_str):
    many(bind2nd(_comment, doc_str_checker))(seq)

def _comment(seq, doc_str_checker):
    if seq.current != '/':
        raise ParseFailed(seq, _comment)
    if doc_str_checker:
        doc_str = seq.peek(doc_str_checker)
        if doc_str:
            raise ParseFailed(seq, _comment)
    s = seq.parse(['//', '/*{{{', '/*'])
    if s == '//':
        seq.parse([until('\n'), until('\r')])
        seq.parse(skip_ws)
    elif s == '/*{{{':
        c = seq.parse(until('}}}*/'))
        if not seq.parse(option('}}}*/')):
            raise ParseError(seq, '}}}*/')
        seq.parse(skip_ws)
    elif s == '/*':
        c = seq.parse(until('*/'))
        if not seq.parse(option('*/')):
            raise ParseError(seq, '*/')
        seq.parse(skip_ws)

from caty.core.schema.base import Annotations, Annotation
def annotation(seq):
    if seq.current != '@':
        return Annotations([])
    seq.parse('@')
    seq.parse('[')
    a = seq.parse(split(_annotation_item, ','))
    seq.parse(']')
    return Annotations(a)

def _annotation_item(seq):
    symbol = seq.parse(Regex(u'[a-zA-Z_][-a-zA-Z0-9_]*'))
    arg = seq.parse(option(_annotation_arg, None))
    return Annotation(symbol, arg)

def _annotation_arg(seq):
    op = seq.parse('(')
    value = seq.parse(parsers)
    cp = seq.parse(')')
    return value

def string_array(seq):
    seq.parse('[')
    values = seq.parse(split(string, ','))
    seq.parse(']')
    return values

class IGNORE: pass

def fragment_name(seq):
    S('#')(seq)
    name = seq.parse(Regex('[a-zA-Z_][-0-9_a-zA-Z]*'))
    return name

