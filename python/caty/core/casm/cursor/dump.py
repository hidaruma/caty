# coding: utf-8
from caty.core.typeinterface import *
from caty.core.schema import *
import caty.jsontools as json

class TreeDumper(TreeCursor):
    def __init__(self, deep=False, withoutdoc=False, recursive=False):
        self.started = False
        self.depth = 0
        self.deep = deep
        self.withoutdoc = withoutdoc
        self.recursive = recursive
        self.context = [None]

    def _visit_root(self, node):
        buff = []
        if not self.started:
            self.started = True
            if node.docstring and not self.withoutdoc:
                buff.append(self._format(node.docstring, self.depth))
            if node.annotations:
                buff.append(node.annotations.to_str())
                buff.append('\n')
            buff.append('type ')
            buff.append(node.name)
            if node.type_params:
                buff.append('<')
                for t in node.type_params:
                    buff.append(t.var_name)
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
                return node.body.accept(self)

    def _format(self, doc, indent):
        r = []
        lines = doc.split('\n')
        for l in lines:
            r.append(' ' * (indent * 4))
            r.append(l.strip())
            r.append('\n')
        return ''.join(r)

    def _visit_scalar(self, node):
        buff = []
        if isinstance(node, TypeReference) and self.deep and self.recursive and node.body and not node.recursive:
            buff.append(node.body.accept(self))
        elif isinstance(node, (TypeReference)):
            buff = [node.name]
            if node.type_args:
                buff.append('<')
                for t in node.type_args:
                    buff.append(t.accept(self))
                    buff.append(', ')
                buff.pop(-1)
                buff.append('>')
        else:
            buff = [node.name]
        self._process_option(node, buff)
        return ''.join(buff)

    def _process_option(self, node, buff):
        if node.options:
            items = [(k, v) for k, v in node.options.items() if k not in ('subName', 'minCount', 'maxCount', 'repeat', '__optional__')]
            if items:
                buff.append('(')
                for k, v in items:
                    buff.append(k)
                    buff.append('=')
                    buff.append('"%s"' % v if isinstance(v, unicode) else u'b"%s"' % v if isinstance(v, str) else str(v))
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
        return node.body.accept(self) + '?'

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
        elif isinstance(e, bool):
            return str(e).lower()
        else:
            return str(e)

    def _visit_object(self, node):
        buff = [u'{\n']
        self.depth += 1
        for k, v in node.items():
            if v.docstring and not self.withoutdoc:
                buff.append('    ' * self.depth)
                buff.append(u'/** %s */' % v.docstring.strip())
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
        if not buff[-1].endswith('?'):
            buff.append('?    ' * self.depth)
        buff.append('\n')
        buff.append('    ' * (self.depth-1))
        buff.append('}')
        self.depth -= 1
        self._process_option(node, buff)
        return ''.join(buff)

    def _visit_array(self, node):
        buff = [u'[']
        self.__vist_iter(node, buff)
        buff.append(u']')
        self._process_option(node, buff)
        return ''.join(buff)

    def __vist_iter(self, node, buff):
        _buff = []
        self.depth += 1
        ls = []
        for c in node:
            ls.append(c)
        if ls:
            for c in ls[:-1]:
                _buff.append(c.accept(self))
                if u'subName' in c.options:
                    _buff.append(' ' + c.options['subName'])
            _buff.append(ls[-1].accept(self))
            if node.repeat:
                _buff.append('*')
            if u'subName' in ls[-1].options:
                _buff.append(' ' + ls[-1].options['subName'])
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
        return buff

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
        buff.insert(0, u'(')
        buff.insert(2, u')')
        self._process_option(node, buff)
        return u''.join(buff)

    def _visit_union(self, node):
        ls = flatten_union(node)
        buff = [u'(']
        for n in ls:
            buff.append(n.accept(self))
            buff.append(u' | ')
        buff.pop(-1)
        buff.append(u')')
        self._process_option(node, buff)
        return u''.join(buff)

    def _visit_updator(self, node):
        l = node.left.accept(self)
        r = node.right.accept(self)
        buff = [l + ' ++ ' + r]
        buff.insert(0, u'(')
        buff.insert(2, u')')
        self._process_option(node, buff)
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

    def _visit_kind(self, node):
        return u'$kind$'
