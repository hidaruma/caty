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
            schema = node.module.get_schema(node.name, len(node.type_args))
            node.body = schema
            type_args = []
            for arg in node.type_args:
                type_args.append(arg.accept(self))
            node.type_args = type_args
        elif isinstance(node, TypeVariable):
            if self.module.has_schema(node.name):
                return self.module.get_schema(node.name)
        return node
