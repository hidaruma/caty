#coding:utf-8
from caty.core.schema.base import TypeVariable
from caty.core.schema.object import PseudoTag as pseudoTag
from caty.core.typeinterface import *
from caty.core.casm.language.ast import *
from caty.core.schema import *
from caty.util.collection import OverlayedDict
import caty.jsontools as json

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

    @apply_annotation
    def _visit_root(self, node):
        self._type_params = node._type_params
        body = node.body.accept(self)
        s = NamedSchema(node.name, node._type_params, body, self.module)
        self._type_params = None
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
                if t.name == node.name:
                    schema = TypeVariable(node.name, node.type_args, node.options, self.module)
                    return schema 
            raise KeyError(node.name)

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

import caty.jsontools as json
class TreeDumper(TreeCursor):
    def __init__(self, deep=False):
        self.started = False
        self.depth = 0
        self.deep = deep

    def _visit_root(self, node):
        buff = []
        if not self.started:
            self.started = True
            if node.docstring:
                buff.append(self._format(node.docstring, self.depth))
            if node.annotations:
                buff.append(node.annotations.to_str())
                buff.append('\n')
            buff.append('type ')
            buff.append(node.name)
            if node.type_params:
                buff.append('<')
                for t in node.type_params:
                    buff.append(t.name)
                    buff.append(', ')
                buff.pop(-1)
                buff.append('>')
            buff.append(' = ')
            buff.append(node.body.accept(self))
            buff.append(';')
            return ''.join(buff)
        else:
            if not self.deep:
                return node.name
            else:
                return node.name + node.body.accept(self)

    def _format(self, doc, indent):
        r = []
        lines = doc.split('\n')
        for l in lines:
            r.append(' ' * (indent * 4))
            r.append(l.strip())
            r.append('\n')
        return ''.join(r)

    def _visit_scalar(self, node):
        buff = [node.name]
        if not isinstance(node, (ScalarSchema, AnySchema, UndefinedSchema, NeverSchema, NullSchema)):
            if node.type_args:
                buff.append('<')
                for t in node.type_args:
                    buff.append(t.accept(self))
                    buff.append(', ')
                buff.pop(-1)
                buff.append('>')
                if isinstance(node, TypeReference):
                    if node.body:
                        buff.append(node.body.accept(self))
        self._process_option(node, buff)
        return ''.join(buff)

    def _process_option(self, node, buff):
        if node.options:
            items = [(k, v) for k, v in node.options.items() if k not in ('subName', 'minCount', 'maxCount')]
            if 'subName' in node.options:
                buff.append(' ' + node.options['subName'])
            if items:
                buff.append('(')
                for k, v in items:
                    buff.append(k)
                    buff.append('=')
                    buff.append(v if isinstance(v, unicode) else str(v))
                    buff.append(', ')
                buff.pop(-1)
                buff.append(')')
            if not (node.options.get('minCount', 1) == 1 and node.options.get('maxCount', 1) == 1):
                buff.append('{')
                if node.options.get('minCount', None) is not None:
                    buff.append(str(node.options['minCount']))
                buff.append(', ')
                if node.options.get('maxCount', None) is not None:
                    buff.append(str(node.options['maxCount']))
                buff.append('}')

    def _visit_option(self, node):
        s = node.body.accept(self)
        for c in ['&', '|', '++', '\n']:
            if c in s:
                return '(%s)?' % s
        return s + '?'

    def _visit_enum(self, node):
        if len(node.enum) > 1:
            buff= ['(', '|'.join(map(self._to_str, node.enum)), ')']
        else:
            buff= ['|'.join(map(self._to_str, node.enum))]
        self._process_option(node, buff)
        return u''.join(buff)

    def _to_str(self, e):
        if isinstance(e, unicode):
            return '"%s"' % e
        else:
            return str(e)

    def _visit_object(self, node):
        buff = ['{\n']
        self.depth += 1
        for k, v in node.items():
            if v.docstring:
                buff.append('    ' * self.depth)
                buff.append(v.docstring.strip())
                buff.append('\n')
            if v.annotations:
                buff.append('    ' * self.depth)
                buff.append(v.annotations.to_str())
                buff.append('\n')

            buff.append('    ' * self.depth)
            buff.append('"%s": ' % k)
            buff.append(v.accept(self))
            buff.append(',\n')

        buff.append('    ' * self.depth)
        buff.append('*: ')
        buff.append(node.wildcard.accept(self))
        buff.append('    ' * self.depth)
        buff.append('\n')
        buff.append('    ' * (self.depth-1))
        buff.append('}')
        self.depth -= 1
        self._process_option(node, buff)
        return ''.join(buff)

    def _visit_array(self, node):
        buff = ['[']
        self.__vist_iter(node, buff)
        buff.append(']')
        self._process_option(node, buff)
        return ''.join(buff)

    def __vist_iter(self, node, buff):
        _buff = []
        self.depth += 1
        for c in node:
            _buff.append(c.accept(self) + ', ')
        if _buff:
            _buff[-1] = _buff[-1].rstrip(', ')
        if isinstance(node, Array) and node.repeat:
            _buff[-1] += '*'
        if filter(lambda s: '\n' in s, _buff):
            for b in _buff:
                buff.append('\n')
                buff.append('    ' * self.depth)
                buff.append(b)
            buff.append('\n')
            buff.append('    ' * (self.depth-1))
        else:
            buff.extend(_buff)
        self.depth -= 1
        return _buff

    def _visit_bag(self, node):
        buff = ['{[']
        self.__vist_iter(node, buff)
        buff.append(']}')
        self._process_option(node, buff)
        return ''.join(buff)

    def _visit_intersection(self, node):
        l = node.left.accept(self)
        r = node.right.accept(self)
        buff = [l + ' & ' + r]
        self._process_option(node, buff)
        if len(buff) > 1:
            buff.insert(0, u'(')
            buff.insert(2, u')')
        return u''.join(buff)

    def _visit_union(self, node):
        l = node.left.accept(self)
        r = node.right.accept(self)
        buff = [l + ' | ' + r]
        self._process_option(node, buff)
        if len(buff) > 1:
            buff.insert(0, u'(')
            buff.insert(2, u')')
        return u''.join(buff)

    def _visit_updator(self, node):
        l = node.left.accept(self)
        r = node.right.accept(self)
        buff = [l + ' ++ ' + r]
        if len(buff) > 1:
            buff.insert(0, u'(')
            buff.insert(2, u')')
        return u''.join(buff)

    def _visit_tag(self, node):
        t = node.tag
        s = node.body.accept(self)
        buff = ['@' + t + ' ' + s]
        self._process_option(node, buff)
        return u''.join(buff)

    def _visit_pseudo_tag(self, node):
        s = node.body.accept(self)
        buff = [ '@?("%s": %s) %s' % (node._name, 
                                    json.pp(node._value),
                                    s)]
        self._process_option(node, buff)
        return u''.join(buff)

class ProfileBuilder(SchemaBuilder):
    def _visit_scalar(self, node):
        if node.name in types:
            return types[node.name].clone(None, node.options)
        elif self.module.has_schema(node.name):
            schema = self.module.get_schema(node.name)
            return schema
        else:
            schema = TypeVariable(node.name, node.type_args, node.options, self.module)
            return schema 

    def _visit_function(self, node):
        from caty.core.casm.cursor.resolver import ReferenceResolver
        from caty.core.exception import CatyException
        if node.profile_container:
            return node
        if node.uri:
            pc = ProfileContainer(node.name, 
                                  node.uri, 
                                  self.module.command_loader, 
                                  node.annotation, 
                                  node.doc, 
                                  node.application, 
                                  node.type_var_names)
        else:
            pc = ScriptProfileContainer(node.name, 
                                        node.script_proxy, 
                                        self.module.command_loader, 
                                        node.annotation, 
                                        node.doc, 
                                        node.application, 
                                        node.type_var_names, 
                                        self.module)

        for p in node.patterns:
            rr = ReferenceResolver(self.module)
            p.build([self, rr])
            e = p.verify_type_var(node.type_var_names)
            if e:
                raise CatyException(u'SCHEMA_COMPILE_ERROR', 
                                    u'Undeclared type variable at $this: $name',
                                    this=node.name, name=e)
            pc.add_profile(CommandProfile(p.opt_schema, p.arg_schema, p.decl))
        return pc

    def _visit_profile(self, node):
        return node


