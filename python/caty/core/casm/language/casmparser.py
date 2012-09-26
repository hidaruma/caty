#coding:utf-8
import re
from topdown import *
from caty.core.casm.language.ast import Provide, ModuleName
from caty.core.language.util import *
from caty.core.casm.language.schemaparser import schema
from caty.core.casm.language.syntaxparser import syntax
from caty.core.casm.language.commandparser import command
from caty.core.casm.language.constparser import const
from caty.core.casm.language.classparser import catyclass
from caty.core.casm.language.kindparser import kind
from caty.core.casm.language.facilityparser import facility
import sys

def parse(t):
    try:
        return as_parser(casm).run(t, hook=remove_comment, auto_remove_ws=True)
    except ParseError as e:
        raise SchemaSyntaxError(e), None, sys.exc_info()[2]

def parse_literate(t):
    try:
        return as_parser(literate_casm).run(t, hook=remove_comment, auto_remove_ws=True)
    except ParseFailed, e:
        raise SchemaSyntaxError(e)

_top_level = [try_(schema), try_(command), try_(syntax), try_(kind), try_(const), try_(catyclass), try_(facility)]

def casm(seq):
    s = []
    #p = option(provides)(seq)
    remove_comment(seq)
    m = module_decl(seq)
    s.append(m)
    #if p:
    #    s.append(p)
    while not seq.eof:
        n = seq.parse(_top_level)
        if n is not IGNORE:
            s.append(n)
    remove_comment(seq)
    return s

def literate_casm(seq):
    s = []
    h = seq.ignore_hook
    seq.ignore_hook = True
    while True:
        x = until(u'<<{')(seq)
        S(u'<<{')(seq)
        if x.endswith('~'):
            continue
        break
    seq.ignore_hook = h
    remove_comment(seq)
    m = module_decl(seq)
    s.append(m)
    while not seq.eof:
        n = seq.parse(_top_level + [peek(S(u'}>>'))])
        if n == u'}>>':
            break
        if n is not IGNORE:
            s.append(n)
    until(u'}>>')(seq)
    S(u'}>>')(seq)
    literal = True
    while not seq.eof:
        h = seq.ignore_hook
        seq.ignore_hook = True
        while literal:
            x = until(u'<<{')(seq)
            if seq.eof:
                break
            S(u'<<{')(seq)
            if x.endswith('~'):
                continue
            literal = False
        if seq.eof:
            break
        seq.ignore_hook = h
        elems = seq.parse(many(_top_level))
        for e in elems:
            if e is not IGNORE:
                s.append(e)
        S(u'}>>')(seq)
        literal = True
    remove_comment(seq)
    return s


def module_decl(seq, type='casm'):
    doc = seq.parse(option(docstring))
    a = seq.parse(annotation)
    _ = seq.parse(keyword('module'))
    n = pkgname(seq)
    if type == 'casm':
        i = seq.parse(option(keyword('in')))
    else:
        i = seq.parse(keyword('in'))
    if i:
        seq.parse(keyword(type))
    if option(keyword('on'))(seq):
        timing = choice(keyword(u'boot'), keyword(u'demand'))(seq)
    else:
        timing = u'boot'
    rel = seq.parse(option(relation, []))
    seq.parse(';')
    return ModuleName(n, a, rel, doc, timing)

def relation(seq):
    seq.parse(keyword('related'))
    return seq.parse([lambda s:[pkgname(s)], pkgnames])

def pkgnames(seq):
    S('[')(seq)
    r = split(pkgname, u',')(seq)
    S(']')(seq)
    return r

def pkgname(seq):
    return seq.parse(Regex(r'[a-zA-Z]+([-a-zA-Z0-9_.])*'))

def provides(seq):
    _ = seq.parse('provides ')
    names = chain_flat(name, comma)
    return Provide(names)

