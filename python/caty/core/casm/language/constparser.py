# coding: utf-8
from caty.core.casm.language.schemaparser import *
from caty.jsontools import xjson

def const(seq):
    doc = option(docstring)(seq)
    a = seq.parse(annotation)
    _ = seq.parse(keyword(u'const'))
    with strict():
        n = seq.parse(name_token)
        if n in RESERVED:
            raise ParseFailed(seq, command, '%s is reserved.' % n)
        if seq.parse(option('::', None)):
            type = typedef(seq)
        else:
            type = None
        seq.parse('=')
        value = peek(choice(_undefined, xjson.parse))(seq) # undefinedとxjsonだけの出現を確認する
        schema = peek(typedef)(seq)
        script = _script(seq)
        nohook(S(u';'))(seq)
        doc2 = postfix_docstring(seq)
        doc = concat_docstring(doc, doc2)
        return ConstDecl(n, type, schema, script, doc, a, value)

def _undefined(seq):
    S('undefined')(seq)
    return UNDEFINED

def _script(seq):
    from caty.core.script.parser import ScriptParser
    p = ScriptParser()
    return choice(*map(try_, [p.value, p.object, p.list, p.tag, p.command]))(seq)



