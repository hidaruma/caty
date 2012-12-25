from HTMLParser import HTMLParser
from topdown import *
__all__ = ['select', 'Element', 'RootNode', 'Text']

def select(string, pattern):
    tb = TreeBuilder()
    tb.feed(string)
    tree = tb.tree
    s = selector.run(pattern)
    return s.select(tree)

class Node(object):
    is_root = False
    def dump(self):
        raise NotImplementedError()

class RootNode(Node):
    is_root = True
    def __init__(self):
        self._childnodes = []

    def add(self, obj):
        self._childnodes.append(obj)

    def dump(self):
        r = []
        for n in self._childnodes:
            r.append(n.dump())
        return ''.join(r)

    to_html = dump

    @property
    def parent(self):
        raise Exception(u'Root node has no parent node.')

    @property
    def child_nodes(self):
        return self._childnodes

    @property
    def text(self):
        return ''.join([t.text for t in self._childnodes])


class PI(Node):
    def __init__(self, pi):
        self._pi = pi

    def dump(self):
        return '<?%s>' % self._pi

    @property
    def text(self):
        return ''

class Decl(Node):
    def __init__(self, decl):
        self._decl = decl

    def dump(self):
        return '<!%s>' % self._decl

    @property
    def text(self):
        return ''

class Text(Node):
    def __init__(self, text):
        self._text = text

    def dump(self):
        return self._text

    @property
    def text(self):
        return self._text

class Element(RootNode):
    empty_elements = [
        'area',
        'base',
        'basefont',
        'br',
        'col',
        'frame',
        'hr',
        'img',
        'input',
        'isindex',
        'link',
        'meta',
        'param',
    ]

    is_root = False
    def __init__(self, tag, attrs, parent):
        RootNode.__init__(self)
        self._tag = tag
        self._attrs = {}
        for n, v in attrs:
            self._attrs[n] = v
        self._parent = parent

    @property
    def parent(self):
        return self._parent

    @property
    def tag(self):
        return self._tag

    @property
    def attrs(self):
        return self._attrs

    def dump(self):
        r = []
        if self._tag not in self.empty_elements:
            r.append(self._open_tag())
            for c in self.child_nodes:
                r.append(c.dump())
            r.append('</%s>' % self._tag)
        else:
            r.append(self._open_close_tag())
        return ''.join(r)

    def _open_tag(self):
        if self.attrs:
            return '<%s %s>' % (self._tag, self._attr_to_str())
        else:
            return '<%s>' % (self._tag)

    def _open_close_tag(self):
        return self._open_tag().replace('>', '/>')

    def _attr_to_str(self):
        r = []
        for k, v in self.attrs.items():
            r.append('%s="%s"' % (k, v))
        return ' '.join(r)

    def to_html(self):
        return self.parent.to_html()

class TreeBuilder(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.node = RootNode()
        self.current = self.node

    def handle_starttag(self, tag, attrs):
        e = Element(tag, attrs, self.current)
        self.current.add(e)
        self.current = e

    def handle_endtag(self, tag):
        self.current = self.current.parent

    def handle_data(self, data):
        self.current.add(Text(data))

    def handle_charref(self, name):
        self.current.add(Text('&%s;' % name))

    def handle_entityref(self, name):
        self.current.add(Text('&%s;' % name))

    def handle_decl(self, decl):
        self.current.add(Decl(decl))

    def handle_pi(self, pi):
        self.current.add(PI(pi))

    @property
    def tree(self):
        if not self.current.is_root:
            raise Exception(u'malformed HTML. One or more tags are mismatched.')
        return self.current

@as_parser
def selector(seq):
    s = seq.parse(split([
                         operational_selector,
                         universal_selector, 
                         type_selector, 
                         ], Regex(' *, *')))
    return SelectorCombinator(s)

class Selector(object):
    def select(self, node):
        raise NotImplementedError()
    
    def find_elements(self, node):
        for n in node.child_nodes:
            if isinstance(n, Element):
                yield n


class SelectorCombinator(Selector):
    def __init__(self, selectors):
        self._selectors = selectors

    def select(self, node):
        found = set()
        for s in self._selectors:
            for n in s.select(node):
                if not n in found:
                    yield n
                    found.add(n)

@try_
def universal_selector(seq):
    seq.parse('*')
    attr = seq.parse(option([attribute, class_attr, id_attr], NullMatcher()))
    return UniversalSelector(attr)

@try_
def attribute(seq):
    skip_ws(seq)
    seq.parse('[')
    skip_ws(seq)
    name = seq.parse(Regex(r'[a-zA-Z0-9_]+'))
    skip_ws(seq)
    eq = seq.parse(option(['=', '~=', '|=']))
    if eq is None:
        skip_ws(seq)
        seq.parse(']')
        return AttributeMatcher(name)
    sep = eq[0]
    skip_ws(seq)
    seq.parse('"')
    value = seq.parse(until('"'))
    seq.parse('"')
    skip_ws(seq)
    seq.parse(']')
    return AttributeMatcher(name, value, sep)

def class_attr(seq):
    seq.parse('.')
    c = seq.parse(Regex(r'[-+a-zA-Z0-9_]+'))
    return AttributeMatcher('class', c)

def id_attr(seq):
    seq.parse('#')
    c = seq.parse(Regex(r'[-+a-zA-Z0-9_]+'))
    return AttributeMatcher('id', c)

class NullMatcher(object):
    def match(self, attrs):
        return True

class AttributeMatcher(NullMatcher):
    def __init__(self, name, value=None, sep='='):
        self._name = name
        self._value = value
        self._sep = sep

    def match(self, attrs):
        if not self._name in attrs:
            return False
        if self._value is None:
            return True
        v = attrs[self._name]
        if self._sep == '=':
            return v == self._value
        elif self._sep == '~':
            return self._value in v.split(' ')
        else:
            return v.split('-')[0] == self._value

class UniversalSelector(Selector):
    def __init__(self, attr_matcher):
        self._attr = attr_matcher

    def is_same_tag(self, t):
        return True

    def select(self, node):
        for n in self.find_elements(node):
            if self._attr.match(n.attrs):
                yield n
            for n2 in self.select(n):
                if self._attr.match(n2.attrs):
                    yield n2

@try_
def type_selector(seq):
    skip_ws(seq)
    t = seq.parse(Regex('[a-zA-Z0-9]+'))
    attr = seq.parse(option([attribute, class_attr, id_attr], NullMatcher()))
    return TypeSelector(t, attr)

class TypeSelector(UniversalSelector):
    def __init__(self, tag, attr_matcher):
        UniversalSelector.__init__(self, attr_matcher)
        self._tag = tag

    def select(self, node):
        for n in UniversalSelector.select(self, node):
            if n.tag == self._tag:
                yield n
    
    def is_same_tag(self, t):
        return self._tag == t

@try_
def operational_selector(seq):
    def descendant_selector(s):
        s.parse(many1(' '))
        return DescendantSelector
    
    def child_selector(s):
        s.parse(Regex(r' *> *'))
        return ChildSelector
    
    def adjacent_selector(s):
        s.parse(Regex(r' *\+ *'))
        return AdjacentSelector
    
    return seq.parse(chainl([universal_selector, type_selector], [child_selector, adjacent_selector, descendant_selector]))


class DescendantSelector(Selector):
    def __init__(self, selector1, selector2):
        self._selector1 = selector1
        self._selector2 = selector2

    def select(self, node):
        for n in self._selector1.select(node):
            for n2 in self._selector2.select(n):
                yield n2

class ChildSelector(Selector):
    def __init__(self, selector1, selector2):
        self._selector1 = selector1
        self._selector2 = selector2

    def select(self, node):
        for n in self._selector1.select(node):
            for n2 in self.find_elements(n):
                if self._selector2.is_same_tag(n2.tag):
                    yield n2

class AdjacentSelector(Selector):
    def __init__(self, selector1, selector2):
        self._selector1 = selector1
        self._selector2 = selector2
    
    def select(self, node):
        for n in self._selector1.select(node):
            nodes = list(self.find_elements(n.parent))
            idx = nodes.index(n)
            if idx < len(nodes) - 1:
                adjacent = nodes[idx+1]
                if self._selector2.is_same_tag(adjacent.tag):
                    yield adjacent


