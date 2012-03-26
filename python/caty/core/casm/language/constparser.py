# coding: utf-8
from caty.core.casm.language.schemaparser import *
from caty.jsontools import xjson

def const(seq):
    doc = option(docstring)(seq)
    a = seq.parse(annotation)
    _ = seq.parse(keyword(u'const'))
    n = seq.parse(name_token)
    if n in RESERVED:
        raise ParseFailed(seq, command, '%s is reserved.' % n)
    if seq.parse(option('::', None)):
        type = typedef(seq)
    else:
        type = None
    seq.parse('=')
    peek(choice(_undefined, xjson))(seq) # undefinedとxjsonだけの出現を確認する
    schema = peek(typedef)(seq)
    script = _script(seq)
    _ = seq.parse(';')
    return ConstDecl(n, type, schema, script, doc, a)

def _undefined(seq):
    S('undefined')
    return UNDEFINED

def _script(seq):
    from caty.core.script.parser import ScriptParser
    p = ScriptParser()
    return choice(*map(try_, [p.value, p.object, p.list, p.tag, p.command]))(seq)



