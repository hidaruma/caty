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
            schema = node.module.get_type(node.name)
            node.body = schema
            type_args = []
            for arg in node.type_args:
                type_args.append(arg.accept(self))
            node.type_args = type_args
        elif isinstance(node, TypeVariable):
            if self.module.has_schema(node.name):
                return self.module.get_type(node.name)
            if node.default and self.module.has_schema(node.default):
                node.set_default(self.module.get_type(node.default))
        return node

    def _visit_kind(self, node):
        return node

    @apply_annotation
    def _visit_tag(self, node):
        t = node.tag
        s = node.body.accept(self)
        if isinstance(t, unicode):
            pass
        elif isinstance(t, SchemaBase):
            t = t.accept(self)
            if isinstance(t, EnumSchema):
                t = t.enum[0]
                if not isinstance(t, unicode):
                    throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'%s' % str(t))
            elif not isinstance(t, StringSchema):
                throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'%s' % t.type)
        else:
            throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'%s' % str(t))
        r = TagSchema(t, s)
        r._options = node.options
        return r

    def _visit_type_function(self, node):
        schema = node.module.get_type(node.typename)
        if node.funcname == u'typeName':
            return EnumSchema([node.typename])
        elif node.funcname == u'recordType':
            if u'__collection' not in schema.annotations:
                throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'Not a collection type: %s' % node.typename)
            return schema.accept(self).body
