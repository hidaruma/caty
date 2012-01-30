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
        else:
            self._mask_scope(node)
        body = node.body.accept(self)
        if r:
            node._schema = body
            self.current = None
            self.type_args = None
            self.real_root = True
            self.history = dict()
            return node
        else:
            self._unmask_scope()
            s = NamedSchema(node.name, node._type_params, body, node.module)
            s._options = node.options
            return s

    def _init_type_params(self, node):
        self.current = node
        self.real_root = False
        parameters = {}
        for v in node.type_params:
            parameters[v.var_name] = v
        self.type_args = OverlayedDict(parameters)

    def _mask_scope(self, node):
        self.scope_stack.append(self.type_args)
        parameters = {}
        for v in node.type_params:
            parameters[v.var_name] = v
        self.type_args = OverlayedDict(parameters)

    def _unmask_scope(self):
        self.type_args = self.scope_stack.pop(-1)

    @apply_annotation
    def _visit_scalar(self, node):
        if isinstance(node, TypeReference):
            self.type_args.new_scope() 
            try:
                arg_memo = [node.name]
                ta = zip(node.type_params, node.type_args)
                for param, type in ta:
                    a = type.accept(self)
                    self.type_args[param.var_name] = a
                    v =  TreeDumper(True).visit(a)
                    arg_memo.append((param.var_name, v))
                key = tuple(arg_memo)
                if key in self.history:
                    return self.history[key]
                r = TypeReference(node.name, node.type_args, node.module)
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
                raise KeyError(node.var_name)
        return node


