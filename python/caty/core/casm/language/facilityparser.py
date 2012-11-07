# coding: utf-8
from caty.core.casm.language.constparser import *
from caty.core.casm.language.constparser import _undefined
from caty.core.casm.language.ast import FacilityNode
from caty.jsontools import xjson
from caty import UNDEFINED

def facility(seq):
    return choice(_facility, _entity)(seq)

@try_
def _facility(seq):
    doc = option(docstring)(seq)
    a = seq.parse(annotation)
    _ = seq.parse(keyword(u'facility'))
    with strict():
        n = seq.parse(name_token)
        if n in RESERVED:
            raise ParseFailed(seq, command, '%s is reserved.' % n)
        seq.parse('=')
        clsname = seq.parse(name_token)
        if option(keyword(u'with'))(seq):
            value = choice(_undefined, xjson.parse)(seq) # undefinedとxjsonだけの出現を確認する
        else:
            value = UNDEFINED
        _ = seq.parse(';')
        return FacilityNode(n, clsname, value, doc, a)

@try_
def _entity(seq):
    doc = option(docstring)(seq)
    a = seq.parse(annotation)
    _ = seq.parse(keyword(u'entity'))
    n = seq.parse(name_token)
    if n in RESERVED:
        raise ParseFailed(seq, command, '%s is reserved.' % n)
    seq.parse('=')
    ename = seq.parse(name_token)
    keyword(u'with')(seq)
    value = choice(_undefined, xjson.parse)(seq) # undefinedとxjsonだけの出現を確認する
    _ = seq.parse(';')
    return EntityNode(n, ename, value, doc, a)
