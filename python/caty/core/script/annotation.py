# coding: utf-8
from caty.core.schema import *
from caty.core.script.builder import CommandCombinator
from caty.core.script.interpreter import BaseInterpreter
from caty.core.script.node import *
from caty.core.std.command.builtin import Void
from caty.core.typeinterface import TreeCursor
from caty.core.command.usage import MiniDumper
import caty.jsontools as json

def hook(f):
    def _(*args, **kwds):
        r = f(*args, **kwds)
        print f, args[1:], r
        return r
    return _

def dump(s):
    return MiniDumper().visit(s)

class ScriptAnnotation(BaseInterpreter):
    u"""内部形式にコンパイルされたCatyスクリプトに対し、型情報の注釈を付けていく。
    """

    def __remove_marker(self, s):
        return s.replace('/*', '').replace('*/', '')

    def __get_canonical_name(self, node):
        if node.profile_container.module and node.profile_container.module.name != 'builtin':
            name = '{0}:{1}'.format(node.profile_container.module.name, node.name)
        else:
            name = node.name
        params = []
        for p in node.profile_container.type_params:
            params.append(p.var_name)
        if not params:
            return name
        else:
            return name+'<%s>' % (', '.join(params))

    def visit(self, node):
        return node.accept(self)

    def visit_command(self, node):
         i = dump(node.in_schema)
         o = dump(node.out_schema)
         return ['/* %s */' % i, self.__get_canonical_name(node),  '/* %s */' % o]

    def visit_script(self, node):
        return node.script.accept(self)

    def visit_pipe(self, node):
        a = node.bf.accept(self)
        b = node.af.accept(self)
        return a + [' | '] + b

    def visit_discard_pipe(self, node):
        a = node.bf.accept(self)
        b = node.af.accept(self)
        return a + [' ;\n '] + b

    def visit_scalar(self, node):
        return [json.pp(node.value)]

    def visit_list(self, node):
        r = ['[']
        i = []
        o = []
        for n in node:
            x = n.accept(self)
            if x[0].startswith('/*'):
                i.append(self.__remove_marker(x.pop(0)))
            if x[-1].startswith('/*'):
                o.append(self.__remove_marker(x.pop(-1)))
            else:
                o.extend(map(lambda a:self.__remove_marker(a), x))
            r.extend(x)
            r.append(', ')

        if r:
            r.pop(-1)
        if i:
            r.insert(0, '/* %s */' % ('&'.join(i)))
        r.append(']')
        if o:
            r.append('/* [%s] */' % (', '.join(o)))
        return r

    def visit_object(self, node):
        r = ['{']
        i = []
        o = {}
        for k, n in node.items():
            x = n.accept(self)
            if x[0].startswith('/*'):
                i.append(self.__remove_marker(x.pop(0)))
            if x[-1].startswith('/*'):
                o[k] = self.__remove_marker(x.pop(-1))
            else:
                o[k] = (map(lambda a:self.__remove_marker(a), x))
            r.extend(x)
            r.append(', ')
        if r:
            r.pop(-1)
        if i:
            r.insert(0, '/* %s */' % ('&'.join(i)))
        r.append('}')
        if o:
            _ = []
            for k, v in o.items():
                _.append('%s: %s' % (k, v))
            r.append('/* {%s} */' % (', '.join(_)))
        return r

    def visit_varstore(self, node):
        raise NotImplementedError(u'{0}#visit_varstore'.format(self.__class__.__name__))

    def visit_varref(self, node):
        raise NotImplementedError(u'{0}#visit_varref'.format(self.__class__.__name__))

    def visit_argref(self, node):
        raise NotImplementedError(u'{0}#visit_argref'.format(self.__class__.__name__))

    def visit_when(self, node):
        raise NotImplementedError(u'{0}#visit_when'.format(self.__class__.__name__))

    def visit_binarytag(self, node):
        raise NotImplementedError(u'{0}#visit_binarytag'.format(self.__class__.__name__))

    def visit_unarytag(self, node):
        raise NotImplementedError(u'{0}#visit_unarytag'.format(self.__class__.__name__))

    def visit_each(self, node):
        raise NotImplementedError(u'{0}#visit_each'.format(self.__class__.__name__))

    def visit_time(self, node):
        raise NotImplementedError(u'{0}#visit_time'.format(self.__class__.__name__))

    def visit_take(self, node):
        raise NotImplementedError(u'{0}#visit_take'.format(self.__class__.__name__))

    def visit_start(self, node):
        raise NotImplementedError(u'{0}#visit_start'.format(self.__class__.__name__))

    def visit_case(self, node):
        raise NotImplementedError(u'{0}#visit_case'.format(self.__class__.__name__))

    def visit_json_path(self, node):
        raise NotImplementedError(u'{0}#visit_json_path'.format(self.__class__.__name__))
