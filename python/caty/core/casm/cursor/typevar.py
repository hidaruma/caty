#coding:utf-8
from caty.core.casm.cursor.base import *
from caty.core.casm.cursor.dump import TreeDumper

class TypeVarApplier(SchemaBuilder):
    def __init__(self, module):
        SchemaBuilder.__init__(self, module)
        self.type_args = None
        self.scope_stack = []
        self.real_root = True
        self.history = dict()
        self.current = None
        self.debug = False

    def visit(self, node):
        try:
            return SchemaBuilder.visit(self, node)
        except:
            print TreeDumper().visit(node)
            raise

    @apply_annotation
    def _visit_root(self, node):
        r = self.real_root
        if r:
            self._init_type_params(node)
        body = node.body.accept(self)
        if self.debug:
            print '>>>>>>', self.dump_scope(), TreeDumper(True).visit(node.body)
        if r:
            node._schema = body
            self.current = None
            self.type_args = None
            self.real_root = True
            self.history = dict()
            return node
        else:
            s = NamedSchema(node.name, node._type_params, body, node.module)
            s._options = node.options
            return s

    def dump_scope(self):
        r = []
        for s in self.type_args.scope:
            o = {}
            for k, v in s.items():
                o[k] = TreeDumper(True).visit(v)
            r.append(o)
        return r

    def _init_type_params(self, node):
        self.current = node
        self.real_root = False
        parameters = {}
        self.type_params = node.type_params
        for v in node.type_params:
            parameters[v.var_name] = v
        self.type_args = OverlayedDict(parameters)

    def _mask_scope(self):
        self.scope_stack.append(self.type_args)
        self.type_args = OverlayedDict({})
        #for p, v in zip(node.type_params, node.type_args):
        #    self.type_args[p.var_name] = v

    def _unmask_scope(self):
        self.type_args = self.scope_stack.pop(-1)

    @apply_annotation
    def _visit_scalar(self, node):
        if isinstance(node, TypeReference):
            self.type_args.new_scope()
            try:
                if self.debug:
                    print '>>', TreeDumper(True).visit(node), node.type_args, node.type_params, self.type_args
                ta = zip(node.type_params, node.type_args)
                args = []
                for param, type in ta:
                    a = type.accept(self)
                    self.type_args[param.var_name] = a
                    args.append(a)
                key = (TreeDumper(True).visit(node), tuple(node.options.items()), tuple(ta))
                if key in self.history:
                    return self.history[key]
                r = TypeReference(node.name, args, node.module)
                self.history[key] = r
                r.body = node.body.accept(self)
                r._options = node.options
                return r
            finally:
                self.type_args.del_scope()
        elif isinstance(node, TypeVariable):
            if node.var_name in self.type_args:
                r = self.type_args[node.var_name]
                if isinstance(r, TypeParam):
                    return node
                else:
                    return r
            else:
                return node
        return node

    def _visit_kind(self, node):
        return node

class TypeParamApplier(SchemaBuilder):
    @apply_annotation
    def _visit_scalar(self, node):
        if isinstance(node, TypeReference):
            self.type_args.new_scope() 
            try:
                ta = zip(node.type_params, node.type_args)
                args = []
                for param, type in ta:
                    a = type.accept(self)
                    args.append(a)
                new_node = TypeReference(node.name, args, node.module)
                new_node.body = node.body
                return new_node
            finally:
                self.type_args.del_scope()
        elif isinstance(node, TypeVariable):
            if node.var_name in self.type_args:
                r = self.type_args[node.var_name]
                if isinstance(r, TypeParam):
                    return node
                else:
                    return r._schema if r._schema else r
            else:
                return node
        return node
