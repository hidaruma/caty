#coding:utf-8
import re
from topdown import *
from caty.core.casm.language.ast import *
from caty.core.language.util import *
from caty.core.casm.language.schemaparser import term, typedef, object_, array, type_arg
from caty.jsontools import xjson
RESERVED = frozenset([
'number', 'integer', 'string', 'boolean', 'array', 'object',
'null', 'true', 'false',
'command',
])


def command(seq):
    try:
        h = seq.parser_hook
        #rmcmt = bind2nd(remove_comment, is_doc_str)
        #seq.parser_hook = ParserHook(skip_ws, rmcmt)
        doc = option(docstring)(seq)
        a = seq.parse(annotation)
        _ = seq.parse(keyword('command'))
        n = seq.parse(cmdname)
        if n in RESERVED:
            raise ParseFailed(seq, command, '%s is reserved.' % n)
        t = seq.parse(option(type_arg, []))
        patterns = many1(call_pattern)(seq)
        j = seq.parse(jump)
        r = seq.parse(many(resource))
        rf = seq.parse(option([script, refers]))
        _ = seq.parse(';')
        return CommandNode(n, map(lambda p:p(j, r), patterns), rf, doc, a, t)
    finally:
        seq.parser_hook = h

def is_doc_str(seq):
    _ = seq.parse(option(docstring))
    if _:
        try:
            seq.parse(skip_ws)
            seq.parse(annotation)
            seq.parse(skip_ws)
            seq.parse(keyword('command'))
            return True
        except:
            return False
    return False

def cmdname(seq):
    return name_token(seq)

def typenames(seq):
    seq.parse('<')
    names = seq.parse(split(name_token, ','))
    seq.parse('>')
    return names

@try_
def call_pattern(seq):
    try:
        _hook = seq.parser_hook
        seq.parser_hook=ParserHook(skip_ws, remove_comment)
        o = option(object_)(seq)
    finally:
        seq.parser_hook = _hook
    if o:
        opt = o
    else:
        opt = None
    a = option(array)(seq)
    if a:
        arg = a
    else:
        arg = None
    _ = seq.parse('::')
    d = decl(seq)
    return lambda j, r: CallPattern(opt, arg, d(j, r))

def decl(seq):
    p = seq.parse(profile)
    return lambda j, r: CommandDecl(p, j, r)

def profile(seq):
    i = typedef(seq)
    _ = seq.parse('->')
    o = typedef(seq)
    return [(i, o)]

def jump(seq):
    t = None
    b = None
    s = None
    r = unordered(throws, breaks, signals)(seq)
    for k, v in r:
        if k == u'throws':
            t = (k, v)
        elif k == 'breaks':
            b = (k, v)
        else:
            s = (k, v)
    return filter(lambda x: x is not None, [t, b, s])

def throws(seq):
    _ = seq.parse(keyword(u'throws'))
    only = seq.parse(option(keyword(u'only')))
    return _, seq.parse([lambda s: [typedef(s)], typelist])

def breaks(seq):
    _ = seq.parse(keyword(u'breaks'))
    return _, seq.parse([lambda s: [typedef(s)], typelist])

def signals(seq):
    _ = seq.parse(keyword(u'signals'))
    return _, seq.parse([lambda s: [typedef(s)], typelist])

def typelist(seq):
    _ = seq.parse('[')
    r = chain_flat(typedef, comma)(seq)
    _ = seq.parse(']')
    return r

def namelist(seq):
    _ = seq.parse('[')
    r = chain_flat(res_name, comma)(seq)
    _ = seq.parse(']')
    return r

def resource(seq):
    return seq.parse([uses, reads, updates])

def updates(seq):
    _ = seq.parse(keyword('uses'))
    return _.strip(), seq.parse([lambda s:[res_name(s)], namelist])

def reads(seq):
    _ = seq.parse(keyword('reads'))
    return _.strip(), seq.parse([lambda s:[res_name(s)], namelist])

def uses(seq):
    _ = seq.parse(keyword('updates'))
    return _.strip(), seq.parse([lambda s:[res_name(s)], namelist])

def res_name(seq):
    n = seq.parse(name)
    p = option(res_param)(seq)
    a = option(alias)(seq)
    return FacilityDecl(n, p, a)

def res_param(seq):
    seq.parse('(')
    p = seq.parse(xjson.parsers)
    seq.parse(')')
    return p

def alias(seq):
    seq.parse(keyword('as'))
    return seq.parse(name)

def refers(seq):
    try:
        return CommandURI(many1(refer)(seq))
    except:

        return CommandURI([('python', 'caty.core.command.Dummy')])

def refer(seq):
    _ = seq.parse(keyword('refers'))
    l = seq.parse(Regex(r'[a-zA-Z]+:'))
    return l.strip(':'), seq.parse(Regex(r'([a-zA-Z][a-zA-Z0-9]*(\.[a-zA-Z][a-zA-Z0-9]*)*)'))

def script(seq):
    from caty.core.script.parser import ScriptParser
    seq.parse('{')
    p = ScriptParser()(seq)
    seq.parse('}')
    return p

