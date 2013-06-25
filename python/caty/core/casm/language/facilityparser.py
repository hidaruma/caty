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
        option(name_token)(seq)
        seq.parse(')')
        config_type = option(parse_config_type, ScalarNode(u'null'))(seq)
        indices_type = option(parse_indices_type, {})(seq)
        ref = option(refer)(seq)
        clsname = None
        if ref:
            clsname = ':'.join(ref)
        nohook(S(u';'))(seq)
        doc2 = postfix_docstring(seq)
        doc = concat_docstring(doc, doc2)
        return FacilityNode(n, clsname, sys_param_type, config_type, indices_type, doc, a)

def parse_config_type(seq):
    keyword(u'configured')(seq)
    return typedef(seq)

def parse_indices_type(seq):
    return choice(conditional_indices, indices)(seq)

def conditional_indices(seq):
    r = {}
    keyword(u'applying')(seq)
    seq.parse('(')
    typename(seq)
    option(name_token)(seq)
    seq.parse(')')
    keyword(u'conforms')(seq)
    S('{')(seq)
    for type, cls_name in split(indices_item, u',', True)(seq):
        if type in r:
            raise ParseError(conditional_indices, seq)
        r[type] = cls_name
    S('}')(seq)
    return r

def indices_item(seq):
    t = choice(typedef, S(u'*'))(seq)
    S('=>')(seq)
    i = choice(index_list, typename)(seq)
    return t, i

def indices(seq):
    keyword(u'conforms')(seq)
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
    tp = choice(keyword(u'master'), keyword(u'entity'))(seq)
    if tp == u'master':
        a.add(Annotation(u'__master'))
    n = seq.parse(name_token)
    if option(nohook(S(u';')))(seq):
        doc2 = postfix_docstring(seq)
        doc = concat_docstring(doc, doc2)
        return EntityNode(n, None, None, doc, a)
    if n in RESERVED:
        raise ParseFailed(seq, command, '%s is reserved.' % n)
    seq.parse('=')
    ename = seq.parse(name_token)
    S(u'(')(seq)
    value = choice(_undefined, xjson.parse)(seq) # undefinedとxjsonだけの出現を確認する
    S(u')')(seq)
    _ = option(parse_indices_type)(seq)
    nohook(S(u';'))(seq)
    doc2 = postfix_docstring(seq)
    doc = concat_docstring(doc, doc2)
    return EntityNode(n, ename, value, doc, a)
