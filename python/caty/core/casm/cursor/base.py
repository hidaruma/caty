#coding:utf-8
from caty.core.schema.base import TypeVariable
from caty.core.schema.object import PseudoTag as pseudoTag
from caty.core.typeinterface import *
from caty.core.casm.language.ast import *
from caty.core.schema import *
from caty.util.collection import OverlayedDict
import caty.jsontools as json
from caty.core.exception import CatyException

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
            for t in self._type_params:
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
        r = TagSchema(t, s)
        r._options = node.options
        return r

    @apply_annotation
    def _visit_pseudo_tag(self, node):
        s = node.body.accept(self)
        s.pseudoTag = pseudoTag(node._name, node._value)
        return s


    def _dereference(self, o, reduce_tag=False):
        if reduce_tag:
            types = (Root, Tag, TypeReference)
        else:
            types = (Root, TypeReference)
        if isinstance(o, types):
            return self._dereference(o.body, reduce_tag)
        else:
            return o


class ProfileBuilder(SchemaBuilder):

    def _visit_function(self, node):
        from caty.core.casm.cursor.resolver import ReferenceResolver
        from caty.core.casm.cursor.typevar import TypeVarApplier
        from caty.core.casm.cursor.normalizer import TypeNormalizer
        from caty.core.exception import CatyException
        self._root_name = node.name
        if node.profile_container:
            return node
        if node.uri:
            pc = ProfileContainer(node.name, 
                                  node.uri, 
                                  self.module.command_loader, 
                                  node.annotation, 
                                  node.doc, 
                                  node.application, 
                                  self.module)
        else:
            pc = ScriptProfileContainer(node.name, 
                                        node.script_proxy, 
                                        self.module.command_loader, 
                                        node.annotation, 
                                        node.doc, 
                                        node.application, 
                                        self.module)

        for pat in node.patterns:
            rr = ReferenceResolver(self.module)
            params = []
            # 型パラメータのデフォルト値を設定
            for p in node.type_params:
                schema = TypeVariable(p.var_name, [], p.kind, p.default, {}, self.module)
                params.append(schema.accept(rr))
            node.type_params = params
            self._type_params = params
            pc.type_params = params
            pat.build([self, rr])
            e = pat.verify_type_var(node.type_var_names)
            if e:
                raise CatyException(u'SCHEMA_COMPILE_ERROR', 
                                    u'Undeclared type variable at $this: $name',
                                    this=node.name, name=e)
            tc = TypeVarApplier(self.module)
            tn = TypeNormalizer(self.module)
            tc.real_root = False
            tc._init_type_params(node)
            opt_schema = tn.visit(pat.opt_schema.accept(tc))
            tc._init_type_params(node)
            arg_schema = tn.visit(pat.arg_schema.accept(tc))
            p = pat.decl.profile
            new_prof = [None, None]
            tc._init_type_params(node)
            new_prof[0] = tn.visit(p[0].accept(tc)) 
            tc._init_type_params(node)
            new_prof[1] = tn.visit(p[1].accept(tc))
            pat.decl.profile = tuple(new_prof)
            pc.add_profile(CommandProfile(pat.opt_schema, pat.arg_schema, pat.decl))
        cmd = pc.get_command_class()
        cmd.profile_container = pc
        return pc

    def _visit_profile(self, node):
        return node

