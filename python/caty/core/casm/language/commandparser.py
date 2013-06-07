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
        _ = seq.parse(keyword(u'command'))
        with strict():
            n = seq.parse(cmdname)
            if n in RESERVED:
                raise ParseFailed(seq, command, '%s is reserved.' % n)
            if option(u':=')(seq):
                ref = identifier_token_m(seq)
                S(u';')(seq)
                return AliasNode(n, ref, u'command')
            t = seq.parse(option(type_arg, []))
            patterns = many1(call_pattern)(seq)
            j = seq.parse(jump)
            r = seq.parse(many(resource))
            rf = seq.parse(option([refers, script]))
            nohook(S(u';'))(seq)
            doc2 = postfix_docstring(seq)
            doc = concat_docstring(doc, doc2)
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
            seq.parse(keyword(u'command'))
            return True
        except:
            return False
    return False

def cmdname(seq):
    return name_token(seq)

def typenames(seq):
    seq.parse(u'<')
    names = seq.parse(split(name_token, ','))
    seq.parse(u'>')
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
    _ = seq.parse(u'::')
    d = decl(seq)
    return lambda j, r: CallPattern(opt, arg, d(j, r))

def decl(seq):
    p = seq.parse(profile)
    return lambda j, r: CommandDecl(p, j, r)

def profile(seq):
    i = typedef(seq)
    _ = seq.parse(u'->')
    o = typedef(seq)
    return (i, o)

def jump(seq):
    t = None
    b = None
    s = None
    r = unordered(try_(throws), try_(signals))(seq)
    for v in r:
        if v.name == u'throws':
            t = v
        else:
            s = v
    return filter(lambda a: a is not None, [t, s])

def throws(seq):
    nothing = option(keyword(u'not'))(seq)
    name = seq.parse(keyword(u'throws'))
    only = None
    types = []
    if not nothing:
        only = seq.parse(option(keyword(u'only')))
        types = seq.parse([typelist, lambda s: [typedef(s)]])
    else:
        only = u'only'
    return Jump(name, types, only, nothing)

def signals(seq):
    nothing = option(keyword(u'not'))(seq)
    name = seq.parse(keyword(u'signals'))
    types = []
    if not nothing:
        types = seq.parse([typelist, lambda s: [typedef(s)]])
    else:
        only = u'only'
    return Jump(name, types, None, nothing)

def typelist(seq):
    _ = seq.parse(u'[')
    r = option(chain_flat(typedef, comma), [])(seq)
    _ = seq.parse(u']')
    return r

def namelist(seq):
    _ = seq.parse(u'[')
    r = chain_flat(res_name, comma)(seq)
    _ = seq.parse(u']')
    return r

def resource(seq):
    return seq.parse([uses, reads, updates])

def updates(seq):
    _ = seq.parse(keyword(u'updates'))
    return _.strip(), seq.parse([lambda s:[res_name(s)], namelist])

def reads(seq):
    _ = seq.parse(keyword(u'reads'))
    return _.strip(), seq.parse([lambda s:[res_name(s)], namelist])

def uses(seq):
    _ = seq.parse(keyword(u'uses'))
    return _.strip(), seq.parse([lambda s:[res_name(s)], namelist])

def res_name(seq):
    n = identifier_token_a(seq)
    p = option(res_param)(seq)
    a = option(alias)(seq)
    return FacilityDecl(n, p, a)

def res_param(seq):
    seq.parse(u'(')
    p = seq.parse(xjson.parsers)
    seq.parse(u')')
    return p

def alias(seq):
    seq.parse(keyword(u'as'))
    return seq.parse(name)

def refers(seq):
    if option(peek(choice('{', '=')))(seq):
        raise ParseFailed(seq, refers)
    try:
        return CommandURI(many1(refer)(seq))
    except:
        return CommandURI([(u'python', 'caty.core.command.Dummy')], False)

def refer(seq):
    _ = seq.parse(keyword(u'refers'))
    l = seq.parse(Regex(r'[a-zA-Z]+:'))
    return l.strip(u':'), seq.parse(Regex(r'([a-zA-Z][a-zA-Z0-9]*(\.[a-zA-Z][a-zA-Z0-9]*)*)'))


from caty.core.script.parser import ScriptParser, CommandProxy, GlobArg, GlobOption
def script(seq):
    option(S(u'='))(seq)
    parser = CommandScriptParser()
    if option(u'{')(seq):
        p = parser(seq)
        seq.parse(u'}')
        return p
    else:
        name = parser.name(seq) 
        ta = option(parser.type_args, [])(seq)
        return CommandProxy(name, ta, [GlobOption()], [GlobArg()], (0, 0))

class CommandScriptParser(ScriptParser):
    def __call__(self, seq):
        self.continue_to_parse = True
        from caty.core.script.proxy import EmptyProxy as Empty
        try:
            r = ScriptParser.__call__(self, seq)
        except:
            r = Empty()
        return r

