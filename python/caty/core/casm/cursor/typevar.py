#coding:utf-8
from caty.core.casm.cursor.base import *

class TypeVarApplier(SchemaBuilder):
    def __init__(self, module):
        SchemaBuilder.__init__(self, module)
        self.type_args = None
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
            self.current = node
            self.real_root = False
            parameters = {}
            for v in node.type_params:
                parameters[v.name] = v
            self.type_args = OverlayedDict(parameters)
        body = node.body.accept(self)
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

    @apply_annotation
    def _visit_scalar(self, node):
        if isinstance(node, TypeReference):
            self.type_args.new_scope() 
            try:
                arg_memo = [node.name]
                ta = zip(node.type_params, node.type_args)
                for param, type in ta:
                    a = type.accept(self)
                    self.type_args[param.name] = a
                    v =  TreeDumper(True).visit(a)
                    arg_memo.append((param.name, v))
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
            if node.name in self.type_args:
                r = self.type_args[node.name]
                if isinstance(r, TypeParam):
                    return node
                else:
                    return r
            else:
                raise KeyError(node.name)
        return node
