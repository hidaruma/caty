class AbsoluteNode(object):
    def accept(self, cursor):
        raise NotImplementedError

class Root(AbsoluteNode):
    def accept(self, cursor):
        return cursor._visit_root(self)

class Scalar(AbsoluteNode):
    def accept(self, cursor):
        return cursor._visit_scalar(self)

class Optional(AbsoluteNode):
    def accept(self, cursor):
        return cursor._visit_option(self)

class Array(AbsoluteNode):
    def accept(self, cursor):
        return cursor._visit_array(self)

    def __iter__(self):
        raise NotImplementedError

class Bag(AbsoluteNode):
    def accept(self, cursor):
        return cursor._visit_bag(self)

    def __iter__(self):
        raise NotImplementedError

class Enum(AbsoluteNode):

    def accept(self, cursor):
        return cursor._visit_enum(self)

    def __iter__(self):
        raise NotImplementedError

class Object(AbsoluteNode):
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

class Function(AbsoluteNode):
    def accept(self, cursor):
        return cursor._visit_function(self)

class Operator(AbsoluteNode):
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

class Tag(AbsoluteNode):
    def accept(self, cursor):
        return cursor._visit_tag(self)

    @property
    def tag(self):
        raise NotImplementedError

class PseudoTag(AbsoluteNode):
    def accept(self, cursor):
        return cursor._visit_pseudo_tag(self)

    @property
    def tag(self):
        raise NotImplementedError(str(self.__class__) + '#tag')

class TreeCursor(object):
    def visit(self, node):
        return node.accept(self)

    def _visit_root(self, node):
        raise NotImplementedError(u'{0}._visit_root'.format(self.__class__.__name__))

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

    @property
    def result(self):
        NotImplementedError

