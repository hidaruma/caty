class AbstractNode(object):
    def accept(self, cursor):
        raise NotImplementedError

class Root(AbstractNode):
    def accept(self, cursor):
        return cursor._visit_root(self)

class Symbol(AbstractNode):
    def accept(self, cursor):
        return cursor._visit_symbol(self)

class Scalar(AbstractNode):
    def accept(self, cursor):
        return cursor._visit_scalar(self)

class Optional(AbstractNode):
    def accept(self, cursor):
        return cursor._visit_option(self)

class Array(AbstractNode):
    def accept(self, cursor):
        return cursor._visit_array(self)

    def __iter__(self):
        raise NotImplementedError

class Bag(AbstractNode):
    def accept(self, cursor):
        return cursor._visit_bag(self)

    def __iter__(self):
        raise NotImplementedError


class Enum(AbstractNode):

    def accept(self, cursor):
        return cursor._visit_enum(self)

    def __iter__(self):
        raise NotImplementedError

class Object(AbstractNode):
    def accept(self, cursor):
        return cursor._visit_object(self)

    def items(self):
        raise NotImplementedError

    def keys(self):
        raise NotImplementedError

    def values(self):
        raise NotImplementedError

    def __getitem__(self, key):
        raise NotImplementedError

    def __setitem__(self, key, value):
        raise NotImplementedError

class Function(AbstractNode):
    def accept(self, cursor):
        return cursor._visit_function(self)

class TypeFunction(AbstractNode):
    def accept(self, cursor):
        return cursor._visit_type_function(self)

class Operator(AbstractNode):
    @property
    def left(self):
        raise NotImplementedError

    @property
    def right(self):
        raise NotImplementedError

class Intersection(Operator):
    def accept(self, cursor):
        return cursor._visit_intersection(self)

class Union(Operator):
    def accept(self, cursor):
        return cursor._visit_union(self)

class Updator(Operator):
    def accept(self, cursor):
        return cursor._visit_updator(self)

class UnaryOperator(AbstractNode):
    def accept(self, cursor):
        return cursor._visit_unary_op(self)

    @property
    def body(self):
        raise NotImplementedError

    @property
    def operator(self):
        raise NotImplementedError

class Tag(AbstractNode):
    def accept(self, cursor):
        return cursor._visit_tag(self)

    @property
    def tag(self):
        raise NotImplementedError

class Ref(object):
    pass

class PseudoTag(AbstractNode):
    def accept(self, cursor):
        return cursor._visit_pseudo_tag(self)

    @property
    def tag(self):
        raise NotImplementedError(str(self.__class__) + '#tag')

class Exponent(object):
    def get_intype(self):
        return self._intype

    def get_outtype(self):
        return self._outtype

    def get_argstype(self):
        return self._argstype

    def get_optstype(self):
        return self._optstype

    def accept(self, cursor):
        return cursor._visit_exponent(self)

class TreeCursor(object):
    def visit(self, node):
        return node.accept(self)

    def _visit_root(self, node):
        raise NotImplementedError(u'{0}._visit_root'.format(self.__class__.__name__))

    def _visit_symbol(self, node):
        raise NotImplementedError(u'{0}._visit_symbol'.format(self.__class__.__name__))

    def _visit_scalar(self, node):
        raise NotImplementedError(u'{0}._visit_scalar'.format(self.__class__.__name__))

    def _visit_option(self, node):
        raise NotImplementedError(u'{0}._visit_option'.format(self.__class__.__name__))

    def _visit_enum(self, node):
        raise NotImplementedError(u'{0}._visit_enum'.format(self.__class__.__name__))

    def _visit_object(self, node):
        raise NotImplementedError(u'{0}._visit_object'.format(self.__class__.__name__))

    def _visit_array(self, node):
        raise NotImplementedError(u'{0}._visit_array'.format(self.__class__.__name__))

    def _visit_bag(self, node):
        raise NotImplementedError(u'{0}._visit_bag'.format(self.__class__.__name__))

    def _visit_intersection(self, node):
        raise NotImplementedError(u'{0}._visit_intersection'.format(self.__class__.__name__))

    def _visit_union(self, node):
        raise NotImplementedError(u'{0}._visit_union'.format(self.__class__.__name__))

    def _visit_updator(self, node):
        raise NotImplementedError(u'{0}._visit_updator'.format(self.__class__.__name__))

    def _visit_tag(self, node):
        raise NotImplementedError(u'{0}._visit_tag'.format(self.__class__.__name__))

    def _visit_pseudo_tag(self, node):
        raise NotImplementedError(u'{0}._visit_pseudo_tag'.format(self.__class__.__name__))

    def _visit_function(self, node):
        raise NotImplementedError(u'{0}._visit_function'.format(self.__class__.__name__))

    def _visit_kind(self, node):
        raise NotImplementedError(u'{0}._visit_kind'.format(self.__class__.__name__))

    def _visit_exponent(self, node):
        raise NotImplementedError(u'{0}._visit_exponent'.format(self.__class__.__name__))

    @property
    def result(self):
        NotImplementedError

    def _dereference(self, o, reduce_tag=False, reduce_option=False):
        return dereference(o, reduce_tag, reduce_option)


def dereference(o, reduce_tag=False, reduce_option=False):
    if reduce_tag:
        if reduce_option:
            types = (Root, Ref, Tag, Optional)
        else:
            types = (Root, Ref, Tag)
    elif reduce_option:
        types = (Root, Ref, Optional)
    else:
        types = (Root, Ref)
    if isinstance(o, types):
        return dereference(o.body, reduce_tag, reduce_option)
    else:
        return o


def flatten_union(node, cache=None, debug=False):
    r = []
    if not cache:
        cache = set()
    if isinstance(node, (Root, Ref)):
        if node.canonical_name in cache:
            return []
        cache.add(node.canonical_name)
    if isinstance(node, Union):
        return [node]
    node = dereference(node)
    if isinstance(node.left, Union):
        r.extend(flatten_union(node.left, cache, debug=debug))
    else:
        cache.add(node.left.canonical_name)
        r.append(node.left)
    if isinstance(node.right, Union):
        r.extend(flatten_union(node.right, cache, debug=debug))
    else:
        cache.add(node.right.canonical_name)
        r.append(node.right)
    return r

def flatten_union_node(node):
    r = []
    if isinstance(node, Union):
        if isinstance(node.left, Union):
            r.extend(flatten_union_node(node.left))
        else:
            r.append(node.left)
        if isinstance(node.right, Union):
            r.extend(flatten_union_node(node.right))
        else:
            r.append(node.right)
    else:
        r.append(node)
    return r

def is_not_usable_type_var(node):
    from caty.core.schema import TypeVariable
    if isinstance(node, TypeVariable):
        if not node._schema and not node.default:
            return True
    return False

def extract_type_var(node):
    from caty.core.schema import TypeVariable
    if isinstance(node, TypeVariable):
        if node._schema:
            return node._schema
        elif node.default:
            return node._default_schema
    elif isinstance(node, UnaryOperator):
        return extract_type_var(node.body)
    return node

class AttrRef(object):

    def __init__(self, name):
        self.name = name

    def __nonzero__(self):
        return False
