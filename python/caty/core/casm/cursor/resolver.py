#coding:utf-8
from caty.core.casm.cursor.base import *
from caty.core.exception import SystemResourceNotFound
from caty.core.casm.language.ast import KindReference, TypeFunctionNode
from caty.core.casm.cursor.dump import TreeDumper

class ReferenceResolver(SchemaBuilder):
    def _visit_root(self, node):
        _ = False
        if self._root_name is None:
            self._root_name = node.name
            self._type_params = node._type_params
            _ = True
        body = node.body.accept(self)
        node._schema = body
        if _:
            self._type_params = None
            self._root_name = None
        return node

    @apply_annotation
    def _visit_symbol(self, node):
        if isinstance(node, TypeReference):
            schema = node.module.get_type(node.name)
            if isinstance(schema, KindReference):
                raise SystemResourceNotFound(u'TypeNotFound', u'$name', name=node.name)
            node.body = schema
            type_args = []
            for arg in node.type_args:
                type_args.append(arg.accept(self))
            a1 = len([a for a in node.type_params if not isinstance(a, NamedTypeParam)])
            a2 = len([b for b in node.type_args if not isinstance(b, NamedParameterNode)])
            if a1 < a2:
                if self._root_name:
                    t = self._root_name + ' = ' + TreeDumper().visit(node)
                else:
                    t = TreeDumper().visit(node)
                throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'Number of type argument does not match: $type', type=t)
            node.type_args = type_args
        elif isinstance(node, TypeVariable):
            if self.module.has_schema(node.name):
                return self.module.get_type(node.name)
            if node.default:
                if self.module.has_schema(node.default):
                    schema = self.module.get_type(node.default)
                    if isinstance(schema, KindReference):
                        raise SystemResourceNotFound(u'TypeNotFound', u'$name', name=node.default)
                    node.set_default(schema)
                else:
                    raise SystemResourceNotFound(u'TypeNotFound', u'$name', name=node.default)
        return node

    def _visit_scalar(self, node):
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
            if isinstance(t, ValueSchema):
                t = t.value
                if not isinstance(t, unicode):
                    throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'%s' % str(t))
            elif isinstance(t, (TypeVariable, TypeReference)):
                pass
            elif not isinstance(t, StringSchema):
                throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'%s' % t.type)
        else:
            throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'%s' % str(t))
        r = TagSchema(t, s)
        r._options = node.options
        return r

    def _visit_type_function(self, node):
        node = TypeFunctionNode(node.funcname, node.typename)
        node.typename = node.typename.accept(self)
        schema = node.typename
        if isinstance(schema, TypeReference):
            schema = schema.body
        elif isinstance(schema, TypeVariable):
            if schema._schema:
                schema = schema._schema
            else:
                return node
        if node.funcname == u'typeName':
            return ValueSchema(schema.canonical_name)
        elif node.funcname == u'keyType':
            from caty.core.casm.language.schemaparser import CasmJSONPathSelectorParser
            if u'__collection' not in schema.annotations:
                debug(schema, schema.annotations)
                throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'Not a collection type: %s' % schema.name)
            path = CasmJSONPathSelectorParser().run(schema.annotations['__identified'].value)
            return path.select(dereference(schema)).next()
        elif node.funcname == u'recordType':
            if u'__collection' not in schema.annotations:
                debug(schema, schema.annotations)
                throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'Not a collection type: %s' % schema.name)
            return schema.accept(self).body

    @apply_annotation
    def _visit_object(self, node):
        o = {}
        for k, v in node.items():
            o[k] = v.accept(self)
        w = node.wildcard.accept(self)
        if w.type == u'undefined':
            w = UndefinedSchema()
        return ObjectSchema(o, w, node.options)

