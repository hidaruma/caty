#coding:utf-8
from caty.core.schema.base import TypeVariable
from caty.core.schema.object import PseudoTag as pseudoTag
from caty.core.typeinterface import *
from caty.core.casm.language.ast import *
from caty.core.schema import *
from caty.util.collection import OverlayedDict
import caty.jsontools as json
from caty.core.exception import CatyException, throw_caty_exception

def apply_annotation(f):
    def _apply(cursor, node):
        s = f(cursor, node)
        if node.annotations:
            s.annotations = node.annotations
        if node.docstring:
            s.docstring = node.docstring
        if node.options:
            s._options = node.options
        return s
    return _apply

class SchemaBuilder(TreeCursor):
    def __init__(self, module):
        self._current_node = None
        self.module = module
        self._root_name = None

    @apply_annotation
    def _visit_root(self, node):
        _ = False
        if self._root_name is None:
            self._root_name = node.name
            _ = True
        self._type_params = node._type_params
        if not node.body:
            body = EmptySchema(node.name)
        else:
            body = node.body.accept(self)
        s = NamedSchema(node.name, node._type_params, body, self.module)
        if _:
            self._type_params = None
            self._root_name = None
        return s

    @apply_annotation
    def _visit_scalar(self, node):
        if self.module.has_ast(node.name):
            type_args = []
            for arg in node.type_args:
                type_args.append(arg.accept(self))
            r = TypeReference(node.name, type_args, self.module)
            r._options = node.options
            return r
        elif node.name in types:
            if node.type_args:
                raise 
            return types[node.name].clone(None, node.options)
        elif self.module.has_schema(node.name):
            type_args = []
            for arg in node.type_args:
                type_args.append(arg.accept(self))
            return TypeReference(node.name, type_args, self.module)
        else:
            for t in self._type_params + self.module.type_params:
                if t.var_name == node.name:
                    schema = TypeVariable(node.name, node.type_args, t.kind, t.default, node.options, self.module)
                    return schema 
            raise CatyException(u'SCHEMA_COMPILE_ERROR', 
                                u'Undeclared type variable at $this: $name',
                                this=self._root_name, name=node.name)

    @apply_annotation
    def _visit_option(self, node):
        s = node.body.accept(self)
        return OptionalSchema(s)

    @apply_annotation
    def _visit_enum(self, node):
        return EnumSchema(node.enum, node.options)

    @apply_annotation
    def _visit_unary_op(self, node):
        if node.operator == u'extract':
            return ExtractorSchema(node.path, node.body.accept(self))
        else:
            return UnaryOpSchema(node.operator, node.body.accept(self), [t.accept(self) for t in node.type_args])

    @apply_annotation
    def _visit_object(self, node):
        o = {}
        for k, v in node.items():
            o[k] = v.accept(self)
        w = node.wildcard.accept(self)
        return ObjectSchema(o, w, node.options)

    @apply_annotation
    def _visit_array(self, node):
        r = []
        for c in node:
            r.append(c.accept(self))
        return ArraySchema(r, node.options)

    @apply_annotation
    def _visit_bag(self, node):
        r = []
        for c in node:
            r.append(c.accept(self))
        return BagSchema(r, node.options)

    @apply_annotation
    def _visit_intersection(self, node):
        l = node.left.accept(self)
        r = node.right.accept(self)
        return IntersectionSchema(l, r, node.options)

    @apply_annotation
    def _visit_union(self, node):
        l = node.left.accept(self)
        r = node.right.accept(self)
        return UnionSchema(l, r, node.options)

    @apply_annotation
    def _visit_updator(self, node):
        l = node.left.accept(self)
        r = node.right.accept(self)
        return UpdatorSchema(l, r, node.options)

    @apply_annotation
    def _visit_tag(self, node):
        t = node.tag
        s = node.body.accept(self)
        if isinstance(t, unicode):
            pass
        elif isinstance(t, Node):
            t = t.accept(self)
        r = TagSchema(t, s)
        r._options = node.options
        return r

    @apply_annotation
    def _visit_pseudo_tag(self, node):
        s = node.body.accept(self)
        s.pseudoTag = pseudoTag(node._name, node._value)
        return s

    def _visit_kind(self, node):
        return node

    def _visit_exponent(self, node):
        print u'[Warning] Not implmented yet'
        return UndefinedSchema()


