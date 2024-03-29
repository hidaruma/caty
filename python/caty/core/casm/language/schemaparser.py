#coding:utf-8
u"""
"""
from caty.core.spectypes import UNDEFINED, INDEF
from topdown import *
from caty.core.casm.language.ast import *
from caty.core.language.util import *
from caty.core.schema import schemata
from caty.jsontools.selector.parser import JSONPathSelectorParser
from caty.core.typeinterface import flatten_union_node
import xjson

RESERVED = frozenset(schemata.keys() + ['type', 'typeName', 'recordType', 'under', 'with', '_', '__'])

def schema(seq):
    doc = option(docstring)(seq)
    annotations = seq.parse(annotation)
    t = seq.parse([keyword('type'), keyword('exception')])
    name_of_type = seq.parse(name_token)
    if t == 'type' and option(u':=')(seq):
        ref = identifier_token_m(seq)
        S(u';')(seq)
        return AliasNode(name_of_type, ref, u'type')
    kind = option(kind_of)(seq)
    redifinable = False
    defined = True
    if kind:
        default = option(default_type)(seq)
    if name_of_type in RESERVED:
        raise ParseFailed(seq, schema, '%s is reserved.' % name_of_type)
    if nohook(option(S(u';')))(seq):
        doc2 = postfix_docstring(seq)
        doc = concat_docstring(doc, doc2)
        return TypeDefNode(name_of_type, [], [], None, annotations, doc, None, False, False)
    type_args = seq.parse(option(type_arg))
    attr_args = seq.parse(option(attr_arg))
    k_of = option(kind_of)(seq)
    e = choice(S(u'='), S(u'?='), S(u'&='))(seq)
    if e == '?=':
        defined = False
    elif e == u'&=':
        redifinable = True
    deferred = seq.parse(option(keyword(u'deferred')))
    if deferred:
        annotations.add(Annotation(u'__deferred'))
        definition = seq.parse(option(typedef))
        if not definition:
            definition = SymbolNode(u'any')
    else:
        definition = seq.parse(typedef)
    if t == 'exception':
        definition = IntersectionNode(TaggedNode(name_of_type, definition), SymbolNode(u'Exception'))
        annotations.add(Annotation(u'__exception'))
        annotations.add(Annotation(u'register-public'))
    else:
        if isinstance(definition, NamedTaggedNode):
            definition._tag = name_of_type
    nohook(S(u';'))(seq)
    doc2 = postfix_docstring(seq)
    doc = concat_docstring(doc, doc2)
    return TypeDefNode(name_of_type, type_args, attr_args, definition, annotations, doc, k_of, defined, redifinable)

def typedef(seq):
    return chainl(annotated_term, op, allow_trailing_operator=True)(seq)

def op(seq):
    o = seq.parse(['&', '|', '++'])
    if o == '&':
        return IntersectionNode
    elif o == '++':
        return UpdatorNode
    else:
        return UnionNode

def term(seq):
    def _tag_exp(s):
        _ = s.parse(u'@')
        _ = s.parse(u'(')
        tl = typedef(s)
        _ = s.parse(u')')
        v = s.parse(option(try_(term)))
        l = map(lambda t:TaggedNode(t, v), flatten_union_node(tl))
        return reduce(lambda a, b: UnionNode(a, b), l)

    def _tag(s):
        _ = s.parse('@')
        t = s.parse([tagname, string, u'*!', u'*'])
        if t == u'*!':
            print u'[WARNING] @*! is deprecated'
            t = SymbolNode(u'explicitTag')
        elif t == u'*':
            print u'[WARNING] @* is deprecated'
            t = SymbolNode(u'anyTag')
        v = s.parse(option(try_(term)))
        return TaggedNode(t, v)

    def _unary(s):
        k = choice(keyword(u'open'), keyword(u'close'), keyword(u'extract'))(s)
        if k == u'extract':
            path = CasmJSONPathSelectorParser()(seq)
            body = s.parse(term)
            return ExtractorNode(path, body)
        elif k == u'close':
            body = s.parse(term)
            return UnaryOpNode(k, body, [])
        else:
            t = seq.parse(option(type_var, []))
            if len(t) > 1:
                raise ParseError(s, _unary)
            body = s.parse(term)
            return UnaryOpNode(k, body, t)

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
        n = seq.parse(option([string, Regex(u'(((\$\.)?[a-zA-Z_][a-zA-Z0-9_.]*)|\$)')], UNDEFINED))
        if n and not n.startswith('$'):
            n = u'$.' + n
        s.parse(':')
        v = s.parse(option([singleton, value], UNDEFINED))
        if n == v == UNDEFINED:
            raise ParseError(s, _pseudo_tag)
        s.parse(')')
        t = s.parse(term)
        r = build_pseudo_tag(n, v, t)
        if r is None:
            raise ParseError(s, _pseudo_tag)
        return r

    def _term(s):
        _ = s.parse('(')
        d = s.parse(typedef)
        _ = s.parse(')')
        return d

    def _never(s):
        _ = s.parse(Regex(r'\(\s*\)'))
        return SymbolNode(u'never', {}, [])

    doc = option(docstring)(seq)
    s = seq.parse(map(try_, [_tag_exp, _pseudo_tag, _type_name_tag, _tag, _never, _unary]) + [enum, _term, bag, object_, array, exponent, type_function, scalar])
    o = seq.parse(option('?'))
    if doc:
        s.docstring = doc
    if o:
        return OptionNode(s)
    else:
        return s

def singleton(seq):
    p = seq.parse([u'undefined', u'null', u'true', u'false', u'indef'])
    if p == 'undefined':
        return UNDEFINED
    elif p == 'null':
        return None
    elif p == 'true':
        return True
    elif p == 'false':
        return False
    elif p == 'indef':
        return INDEF

def tagname(seq):
    return seq.parse(Regex(u'[a-zA-Z0-9_][a-zA-Z0-9-_]*'))

def type_arg(seq):
    _ = seq.parse('<')
    named = option(chain_flat(named_type_paramater, comma), [])(seq)
    positional = chain_flat(type_paramater, comma)(seq)
    _ = seq.parse('>')
    return named + positional

@try_
def named_type_paramater(seq):
    doc = option(docstring)(seq)
    arg_name = name_token(seq)
    S(u'=')(seq)
    name = name_token(seq)
    kind = option(kind_of)(seq)
    default = option(default_type)(seq)
    return NamedTypeParam(arg_name, name, kind, default)

def type_paramater(seq):
    doc = option(docstring)(seq)
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
        named_params = option(chain_flat(named_typedef, comma), [])(seq)
        params = chain_flat(typedef, comma)(seq)
        _ = seq.parse('>')
        return named_params + params

@try_
def named_typedef(seq):
    arg_name = name_token(seq)
    S(u'=')(seq)
    body = typedef(seq)
    return NamedParameterNode(arg_name, body)

def scalar(seq):
    n = seq.parse(typename)
    t = seq.parse(option(type_var, []))
    o = seq.parse(option(options, {}))
    node = SymbolNode(n, o, t)
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
    v = choice(xjson.parse, attr_ref)(seq)
    return [k, v]

def attr_ref(seq):
    S(u'%')(seq)
    return AttrRef(name(seq))

def bag(seq):
    seq.parse('{[')
    r = seq.parse(option(chain_flat(bag_type, comma), []))
    seq.parse(']}')
    o = seq.parse(option(options, {}))
    return BagNode(r, o)

def bag_type(seq):
    s = seq.parse(annotated_typedef)
    _ = seq.parse(option('{'))
    if not _:
        if isinstance(s, OptionNode):
            s = s.body
            s.options['minCount'] = 0
            s.options['maxCount'] = 1
            return s
        else:
            return s
    else:
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
    s = seq.parse([annotated_typedef, loose_item])
    r = seq.parse(option('*'))
    n = seq.parse(option(name))
    if n:
        s.options['subName'] = n
    return [s, r]

def annotated_typedef(seq):
    doc = seq.parse(option(docstring))
    a = seq.parse(option(annotation, Annotations([])))
    s = typedef(seq)
    s.annotations = a
    if doc:
        s.docstring = doc
    return s

def annotated_term(seq):
    doc = seq.parse(option(docstring))
    a = seq.parse(option(annotation))
    s = term(seq)
    if a:
        s.annotations = a
    if doc:
        s.docstring = doc
    return s

def loose_item(seq):
    from caty import UNDEFINED
    if not seq.peek(option(comma)):
        raise ParseFailed(seq, array)
    return SymbolNode(u'undefined')

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
    v = maybe_tagged_value(seq)
    return ScalarNode(v)

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
        # ワイルドカードの正規化
        if not isinstance(w, OptionNode):
            w = OptionNode(w)
        w = _normalize_option(w)
    return ObjectNode(items, w, o)

def _normalize_option(node):
    if isinstance(node, OptionNode):
        w = _normalize_option(node.body)
        if isinstance(w, SymbolNode):
            if w.name == u'undefined':
                w.docstring = node.docstring
                return w
            elif w.name == u'never':
                w.name = u'undefined'
                w.docstring = node.docstring
                return w
            else:
                return node
        elif isinstance(w, OptionNode):
            w.docstring = node.docstring
            return w
    return node

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
            elif isinstance(obj, Tag):
                for r in self.run(obj.body):
                    yield r
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
            elif isinstance(obj, Tag):
                for r in self.run(obj.body):
                    yield r
            else:
                raise Exception('not a array')

        def _to_str(self):
            return str(self.property)

    class TagContentSelector(Selector):
        def __init__(self, src):
            Selector.__init__(self)
            self.src= src

        def run(self, obj):
            from caty.core.typeinterface import Tag
            from caty.core.exception import throw_caty_exception
            if not isinstance(obj, Tag):
                throw_caty_exception(u'SchemaCompileError',
                    u'Unsupported operand type for $op: $type',
                    op=u'content', type=obj.type)
            yield obj.body

        def _to_str(self):
            return self.src

    def __init__(self):
        JSONPathSelectorParser.__init__(self, False, True, self)

    def namewildcard(self, seq):
        t = seq.parse('*')
        raise ParseError(seq, t)

    def itemwildcard(self, seq):
        t = seq.parse('#')
        raise ParseError(seq, t)

    def oldtag(self, seq):
        t = seq.parse('^')
        raise ParseError(seq, t)

    def tag(self, seq):
        t = seq.parse('tag()')
        raise ParseError(seq, t)

    def exp_tag(self, seq):
        t = seq.parse('exp-tag()')
        raise ParseError(seq, t)
 
    def length(self, seq):
        t = seq.parse('length()')
        raise ParseError(seq, t)

@try_
def exponent(seq):
    keyword(u'command')(seq)
    ta = option(type_arg)(seq)
    with strict():
        opts = option(object_)(seq)
        args = option(array)(seq)
        S(u'::')(seq)
        intype = term(seq)
        S(u'->')(seq)
        outtype = term(seq)
        return ExponentNode(intype, outtype, args, opts)

def type_function(seq):
    t = choice(keyword(u'typeName'), keyword(u'recordType'), keyword(u'keyType'))(seq)
    S(u'<')(seq)
    n = seq.parse(typename)
    S(u'>')(seq)
    node = TypeFunctionNode(t, n)
    return node

def attr_arg(seq):
    S(u'(')(seq)
    args = split(name, u',', allow_last_delim=True)(seq)
    S(u')')(seq)
    return args

def build_pseudo_tag(path, value, node):
    if isinstance(node, PseudoTaggedNode):
        if not ((node._name is UNDEFINED and path is not UNDEFINED and node._value is not UNDEFINED and value is UNDEFINED) 
               or (node._name is not UNDEFINED and path is UNDEFINED and node._value is UNDEFINED and value is not UNDEFINED)):
            return None
        if node._name is UNDEFINED:
            return build_pseudo_tag(path, node._value, node.body)
        else:
            return build_pseudo_tag(node._name, value, node.body)
    elif isinstance(node, OperatorNode):
        l = build_pseudo_tag(path, value, node.left)
        r = build_pseudo_tag(path, value, node.right)
        return node.__class__(l, r)
    elif isinstance(node, TaggedNode):
        s = build_pseudo_tag(path, value, node.body)
        return TaggedNode(node.tag, s)
    else:
        return PseudoTaggedNode(path, value, node)

