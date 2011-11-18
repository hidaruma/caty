from topdown import *
from caty.core.casm.language.schemaparser import *
from caty.jsontools import stdjson

def syntax(seq):
    doc = option(docstring)(seq)
    a = seq.parse(annotation)
    t = seq.parse(keyword('syntax'))
    n = seq.parse(name_token)
    if n in RESERVED:
        raise ParseFailed(seq, schema, '%s is reserved.' % n)
    v = seq.parse(option(type_arg))
    e = seq.parse(['=', '::='])
    a.add(Annotation(u'__syntax'))
    if e == '::=':
        bnf = seq.parse(bnf_def)
        if seq.parse([':=', '=', ';']) == ';':
            a.add(Annotation(u'__deferred'))
            d = ScalarNode(u'any')
            return ASTRoot(n, v, d, a, doc)
    deferred = seq.parse(option(keyword('deferred')))
    if deferred:
        a.add(Annotation(u'__deferred'))
        d = seq.parse(option(typedef))
        if not d:
            d = ScalarNode(u'any')
    else:
        d = seq.parse(typedef)
    if d.optional:
        raise ParseFailed(seq, schema)
    if t == 'exception':
        d = IntersectionNode(TaggedNode(n, d), ScalarNode(u'Exception'))
        a.add(Annotation('__exception'))
        a.add(Annotation('register-public'))
    d.apply_type_name(n)
    c = seq.parse(';')
    return ASTRoot(n, v, d, a, doc)

def bnf_def(seq):
    seq.parse(many(['??', '(:', ':)', name_token, integer, string, sq_string, '|', '@&', '?', '*', '{', '}', '(', ')', ':', '<', '>', ',', '@']))

@try_
def sq_string(seq):
    def series_of_escape(s):
        import itertools
        return len(list(itertools.takewhile(lambda c: c=='\\', reversed(s))))
    try:
        seq.ignore_hook = True
        st = [seq.parse("'")]
        s = seq.parse(until("'"))
        while True:
            if series_of_escape(s) % 2 == 0:
                st.append(s)
                break
            else:
                st.append(s)
                s = seq.parse(Regex(r"'[^']*"))
        st.append(seq.parse("'"))
        return stdjson.loads('"%s"' % ''.join(st[1:-1]))
    except EndOfBuffer, e:
        raise ParseFailed(seq, string)
    finally:
        seq.ignore_hook = False

