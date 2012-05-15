#coding:utf-8
from caty.core.casm.cursor.base import *

class ReferenceResolver(SchemaBuilder):
    def _visit_root(self, node):
        body = node.body.accept(self)
        node._schema = body
        return node

    @apply_annotation
    def _visit_scalar(self, node):
        if isinstance(node, TypeReference):
            schema = node.module.get_schema(node.name)
            node.body = schema
            type_args = []
            for arg in node.type_args:
                type_args.append(arg.accept(self))
            node.type_args = type_args
        elif isinstance(node, TypeVariable):
            if self.module.has_schema(node.name):
                return self.module.get_schema(node.name)
            if node.default and self.module.has_schema(node.default):
                node.set_default(self.module.get_schema(node.default))
        return node

