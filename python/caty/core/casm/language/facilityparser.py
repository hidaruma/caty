# coding: utf-8
from caty.core.casm.language.constparser import *
from caty.core.casm.language.constparser import _undefined
from caty.core.casm.language.commandparser import refer
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
        seq.parse('(')
        sys_param_type = typename(seq)
        seq.parse(')')
        config_type = option(parse_config_type, ScalarNode(u'null'))(seq)
        indices_type = option(parse_indices_type, {})(seq)
        ref = option(refer)(seq)
        clsname = None
        if ref:
            clsname = ':'.join(ref)
        _ = seq.parse(';')
        return FacilityNode(n, clsname, sys_param_type, config_type, indices_type, doc, a)

def parse_config_type(seq):
    keyword(u'configured')(seq)
    return typedef(seq)

def parse_indices_type(seq):
    keyword(u'conforms')(seq)
    return choice(conditional_indices, indices)(seq)

def conditional_indices(seq):
    r = {}
    S('{')(seq)
    for type, cls_name in split(indices_item, u',', True)(seq):
        r[type] = cls_name
    S('}')(seq)
    return r

def indices_item(seq):
    t = typedef(seq)
    S('=>')(seq)
    i = indices(seq)
    return t, i

def indices(seq):
    return choice(index_list, typename)(seq)

def index_list(seq):
    S('[')(seq)
    r = split(typename, ',', True)
    S(']')(seq)
    return r

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
    S(u'(')(seq)
    value = choice(_undefined, xjson.parse)(seq) # undefinedとxjsonだけの出現を確認する
    S(u')')(seq)
    _ = option(parse_indices_type)(seq)
    _ = seq.parse(';')
    return EntityNode(n, ename, value, doc, a)
