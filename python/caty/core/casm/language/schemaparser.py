#coding:utf-8
u"""
"""
from caty import UNDEFINED
from topdown import *
from caty.core.casm.language.ast import *
from caty.core.language.util import *
from caty.core.schema import schemata
from caty.jsontools.selector.parser import JSONPathSelectorParser

RESERVED = frozenset(schemata.keys() + ['type'])

def schema(seq):
    doc = option(docstring)(seq)
    annotations = seq.parse(annotation)
    t = seq.parse([keyword('type'), keyword('exception')])
    name_of_type = seq.parse(name_token)
    if name_of_type in RESERVED:
        raise ParseFailed(seq, schema, '%s is reserved.' % n)
    type_args = seq.parse(option(type_arg))
    k_of = option(kind_of)(seq)
    e = seq.parse('=')
    deferred = seq.parse(option(keyword(u'deferred')))
    if deferred:
        annotations.add(Annotation(u'__deferred'))
        definition = seq.parse(option(typedef))
        if not definition:
            definition = ScalarNode(u'any')
    else:
        definition = seq.parse(typedef)
    if t == 'exception':
        definition = IntersectionNode(TaggedNode(name_of_type, definition), ScalarNode(u'Exception'))
        annotations.add(Annotation(u'__exception'))
        annotations.add(Annotation(u'register-public'))
    else:
        if isinstance(definition, NamedTaggedNode):
            definition._tag = name_of_type
    c = seq.parse(';')
    return ASTRoot(name_of_type, type_args, definition, annotations, doc)

def typedef(seq):
    return chainl(term, op, allow_trailing_operator=True)(seq)

def op(seq):
    o = seq.parse(['&', '|', '++'])
    if o == '&':
        return IntersectionNode
    elif o == '++':
        return UpdatorNode
    else:
        return UnionNode

def term(seq):
    def _tag(s):
        _ = s.parse('@')
        t = s.parse([tagname, string, u'*!', u'*'])
        v = s.parse(option(try_(term)))
        return TaggedNode(t, v)

    def _unary(s):
        k = choice(keyword(u'open'), keyword(u'close'), keyword(u'extract'))(s)
        if k == u'extract':
            path = CasmJSONPathSelectorParser()(seq)
            body = s.parse(typedef)
            return ExtractorNode(path, body)
        else:
            body = s.parse(typedef)
            return UnaryOpNode(k, body)

    def _type_name_tag(s):
        _= s.parse('@&')
        v = s.parse(term)
        return NamedTaggedNode(v)
    
    def _obj_term(s):
        s.parse('(')
        o = s.parse([object_, _obj_term])
        s.parse(')')
        return o

    def _pseudo_tag(s):
        s.parse('@?')
        s.parse('(')
        n = seq.parse([string, Regex(u'(([a-zA-Z_][a-zA-Z0-9_]*)|\$)')])
        s.parse(':')
        v = s.parse([singleton, value])
        s.parse(')')
        t = s.parse(term)
        return PseudoTaggedNode(n, v, t)

    def _term(s):
        _ = s.parse('(')
        d = s.parse(typedef)
        _ = s.parse(')')
        return d

    def _never(s):
        _ = s.parse(Regex(r'\(\s*\)'))
        return ScalarNode(u'never', {}, [])

    doc = option(docstring)(seq)
    s = seq.parse(map(try_, [_pseudo_tag, _type_name_tag, _tag, _never, _unary]) + [enum, _term, bag, object_, array, scalar])
    o = seq.parse(option('?'))
    if doc:
        s.docstring = doc
    if o:
        return OptionNode(s)
    else:
        return s

def singleton(seq):
    p = seq.parse(['undefined', 'null', 'true', 'false'])
    if p == 'undefined':
        return UNDEFINED
    elif p == 'null':
        return None
    elif p == 'true':
        return True
    elif p == 'false':
        return False

def tagname(seq):
    return seq.parse(Regex(u'[a-zA-Z0-9_][a-zA-Z0-9-_]*'))

def type_arg(seq):
    _ = seq.parse('<')
    vars = chain_flat(type_paramater, comma)(seq)
    _ = seq.parse('>')
    return vars

def type_paramater(seq):
    name = name_token(seq)
    kind = option(kind_of)(seq)
    default = option(default_type)(seq)
    return TypeParam(name, kind, default)

def kind_of(seq):
    seq.parse(keyword('in'))
    return seq.parse(typename)

def default_type(seq):
    seq.parse(keyword('default'))
    return seq.parse(typename)

@try_
def type_var(seq):
    _ = seq.parse('<')
    with strict():
        vars = chain_flat(typedef, comma)(seq)
        _ = seq.parse('>')
        return vars

def scalar(seq):
    n = seq.parse(typename)
    o = seq.parse(option(options, {}))
    t = seq.parse(option(type_var, []))
    node = ScalarNode(n, o, t)
    return node

def typename(seq):
    return identifier_token_a(seq)
    #return seq.parse(Regex(r'(([a-zA-Z_][a-zA-Z0-9_]*#)?(\.[_a-zA-Z][_a-zA-Z0-9]*)*\:)?(([_a-zA-Z][_a-zA-Z0-9]*)|(\$))'))

def options(seq):
    _ = seq.parse('(')
    opts = option(chain_flat(optval, comma))(seq)
    _ = seq.parse(')')
    if not opts: return {}
    return dict(opts)

def optval(seq):
    k = seq.parse(name)
    _ = seq.parse('=')
    v = seq.parse(value)
    return [k, v]

def bag(seq):
    seq.parse('{[')
    r = seq.parse(option(chain_flat(bag_type, comma), []))
    seq.parse(']}')
    o = seq.parse(option(options, {}))
    return BagNode(r, o)

def bag_type(seq):
    s = seq.parse(term)
    _ = seq.parse(option('{'))
    if not _:
        return s
    a = int(seq.parse(Regex(r'([0-9])|([1-9][0-9]+)')))
    _ = seq.parse(option(',', False))
    if _:
        b = seq.parse(option(Regex(r'([0-9])|([1-9][0-9]+)'), None))
    else:
        b = a
    seq.parse('}')
    s.options['minCount'] = a
    s.options['maxCount'] = int(b) if b else b
    return s

def array(seq):
    seq.parse('[')
    with strict():
        r = option(chain_flat(repeatable_type, comma), [])(seq)
        seq.parse(']')
        o = seq.parse(option(options, {}))
        o['repeat'] = False
        l = []
        for s, opt in r:
            if opt == '*':
                o['repeat'] = True
            l.append(s)
        a = ArrayNode(l, o)
        return a

def repeatable_type(seq):
    s = seq.parse([annotated_term, loose_item])
    r = seq.parse(option('*'))
    n = seq.parse(option(name))
    if n:
        s.options['subName'] = n
    return [s, r]

def annotated_term(seq):
    doc = seq.parse(option(docstring))
    a = seq.parse(option(annotation, Annotations([])))
    s = typedef(seq)
    s.annotations = a
    if doc:
        s.docstring = doc
    return s

def loose_item(seq):
    from caty import UNDEFINED
    if not seq.peek(option(comma)):
        raise ParseFailed(seq, array)
    return ScalarNode(u'undefined')

def maybe_tagged_value(seq):
    @try_
    def _tagged(s):
        _ = s.parse('@')
        t = s.parse([name, '*'])
        v = s.parse(value)
        return TaggedNode(t, v)
    return seq.parse([_tagged, value])

def enum(seq):
    #values = seq.parse(chain_flat(maybe_tagged_value, '|'))
    v = [maybe_tagged_value(seq)]
    return EnumNode(v)

def object_(seq):
    _ = seq.parse('{')
    items = {}
    ls = option(chain_flat(item, comma), [])(seq)
    for k, v in ls:
        if k in items:
            raise KeyError(k)
        items[k] = v
    _ = seq.parse('}')
    o = seq.parse(option(options, {}))
    w = None
    if '*' in items:
        w = items['*']
        del items['*']
    return ObjectNode(items, w, o)

def item(seq):
    doc = seq.parse(option(docstring))
    d = seq.parse(option(annotation, Annotations([])))
    k = seq.parse([string, '*'])
    _ = seq.parse(':')
    s = typedef(seq)
    s.annotations = d
    if doc:
        s.docstring = doc
    return [k, s]

from caty.jsontools.selector.stm import Nothing, Selector, SelectorWrapper, AllSelector
class CasmJSONPathSelectorParser(JSONPathSelectorParser):
    SelectorWrapper = SelectorWrapper
    AllSelector = AllSelector
    class PropertySelector(Selector):
        def __init__(self, prop, opt=False):
            Selector.__init__(self)
            self.property = prop
            self.is_optional = opt

        def run(self, obj, ignored=False):
            if isinstance(obj, Object):
                if self.property in obj:
                    yield obj[self.property]
                else:
                    raise KeyError(self.property)
            else:
                #if not self.is_optional:
                raise Exception('not a object')

        def _to_str(self):
            return self.property if ' ' not in self.property else '"%s"' % self.property

    class ItemSelector(Selector):
        def __init__(self, prop, optional=False):
            Selector.__init__(self)
            self.property = prop
            self.is_optional = optional

        def run(self, obj, ignored=False):
            if isinstance(obj, Array):
                if len(obj) > self.property:
                    yield obj[self.property]
                else:
                    raise IndexError(str(self.property))
            else:
                raise Exception('not a array')

        def _to_str(self):
            return str(self.property)

    class TagContentSelector(Selector):
        def __init__(self, src):
            Selector.__init__(self)
            self.src= src

        def run(self, obj):
            yield obj.body

        def _to_str(self):
            return self.src

    def __init__(self):
        JSONPathSelectorParser.__init__(self, False, True, self)

