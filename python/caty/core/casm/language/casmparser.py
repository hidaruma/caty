#coding:utf-8
import re
from topdown import *
from caty.core.casm.language.ast import Provide, ModuleName
from caty.core.language.util import *
from caty.core.casm.language.schemaparser import schema
from caty.core.casm.language.syntaxparser import syntax
from caty.core.casm.language.commandparser import command
from caty.core.casm.language.kindparser import kind

def parse(t):
    try:
        return as_parser(casm).run(t, hook=remove_comment, auto_remove_ws=True)
    except ParseFailed, e:
        raise SchemaSyntaxError(e)

def iparse(t):
    try:
        return (i for i in as_parser(casm).run(t, hook=remove_comment, auto_remove_ws=True))
    except ParseFailed, e:
        raise SchemaSyntaxError(e)

def iparse_literate(t):
    try:
        return (i for i in as_parser(literate_casm).run(t, hook=remove_comment, auto_remove_ws=True))
    except ParseFailed, e:
        raise SchemaSyntaxError(e)

def casm(seq):
    s = []
    #p = option(provides)(seq)
    remove_comment(seq)
    m = module_decl(seq)
    s.append(m)
    #if p:
    #    s.append(p)
    while not seq.eof:
        n = seq.parse([try_(schema), try_(command), try_(syntax), try_(kind)])
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
    until(u'}>>')(seq)
    S(u'}>>')(seq)
    while not seq.eof:
        h = seq.ignore_hook
        seq.ignore_hook = True
        while True:
            x = until(u'<<{')(seq)
            S(u'<<{')(seq)
            if x.endswith('~'):
                continue
            break
        seq.ignore_hook = h
        n = seq.parse([try_(schema), try_(command), try_(syntax), try_(kind)])
        if n is not IGNORE:
            s.append(n)
        until(u'}>>')(seq)
        S(u'}>>')(seq)
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
    seq.parse(option(on_phrase))
    seq.parse(';')
    return ModuleName(n, a, doc)

def on_phrase(seq):
    seq.parse(keyword('on'))
    seq.parse(['boot', 'demand', 'never'])

def pkgname(seq):
    return seq.parse(Regex(r'[a-zA-Z]+([-a-zA-Z0-9_.])*'))

def provides(seq):
    _ = seq.parse('provides ')
    names = chain_flat(name, comma)
    return Provide(names)

