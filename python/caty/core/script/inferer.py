# coding: utf-8
from caty.core.schema import *
from caty.core.script.builder import CommandCombinator
from caty.core.script.interpreter import BaseInterpreter
from caty.core.script.node import *
from caty.core.std.command.builtin import Void
from caty.core.typeinterface import TreeCursor
from caty.core.command.usage import MiniDumper
import caty.jsontools as json


class TypeInferer(BaseInterpreter):
    u"""
    コマンドの入出力型を比較し、型の包含関係の判定と型推論を行う。
    a | bというパイプラインにおいて、aの出力型がbの入力型に包含されていない場合、エラーとなる。
    a :: string -> number, b :: boolean -> stringなどはエラーとなる例である。
    a<S> :: string -> T, b<T> :: T -> stringなどとなっている場合はエラーにならないが、
    実行時エラーの可能性は排除できない。
    a<S> :: string -> T, b<T> :: T -> T, c :: integer -> booleanなどの場合、
    Tがintegerだと推論され、続いてS=T=integerと推論される。
    型の比較結果はメッセージのリストとして返され、エラーを含む場合はNGでタグ付けされ、正常な場合はOKでタグ付けされる。
    """
    def __init__(self):
        BaseInterpreter.__init__(self)
        self.namespaces = [{}]
        self.__messages = []
        self.__cache = {}

    @property
    def message(self):
        return u'\n    '.join([u'[ERROR] Failed to type check']+self.__messages)

    @property
    def is_error(self):
        return len(self.__messages) > 0

    def find_name(self, name):
        for n in reversed(self.namespaces):
            if name in n:
                return n[name]
        return TypeVariable(name, [], {}, None)

    def visit_command(self, node):
        if node in self.__cache:
            return self.__cache[node]
        else:
            c = FunctionType(node.in_schema, node.out_schema, node.profile_container.type_var_names)
            self.__cache[node] = c
            return c

    def visit_pipe(self, node):
        a = node.bf.accept(self)
        b = node.af.accept(self)
        tc = TypeComparator(a, b)
        tc.compare()
        if tc.is_error:
            self.__messages.extend(tc.error_messages)
        if isinstance(node.af, VarStore):
            self.namespaces[-1][node.af.var_name] = r.output_type
        return FunctionType(tc.input_type, tc.output_type, tc.type_vars)

    def visit_discard_pipe(self, node):
        a = node.bf.accept(self)
        b = node.af.accept(self)
        return b

    def visit_scalar(self, node):
        return FunctionType(VoidSchema(), EnumSchema([node.value]))

    def visit_list(self, node):
        o = []
        for i in node:
            x = i.accept(self)
            o.append(x.output_type)
        return FunctionType(VoidSchema(), ArraySchema(o))

    def visit_object(self, node):
        o = {}
        for k, v in node.iteritems():
            x = i.accept(self)
            o[k] = x.output_type
        return FunctionType(VoidSchema(), ObjectSchema(o))

    def visit_varstore(self, node):
        return FunctionType(node.in_schema, node.out_schema, node.profile_container.type_var_names)

    def visit_varref(self, node):
        return FunctionType(VoidSchema(), self.find_name(node.var_name))

    def visit_argref(self, node):
        return FunctionType(VoidSchema(), self.find_name(node.arg_num))

    def visit_when(self, node):
        i = None
        o = None
        for k, v in node.cases.iteritems():
            t = v.cmd.accept(self)
            if not i:
                i = TagSchema(i, t.input_type)
                o = t.output_type
            else:
                i = UnionSchema(i, t.input_type)
                try:
                    o = UnionSchema(o, t.output_type)
                except:
                    # XXX:
                    # when分岐の出力はUnionだが、必ずしも排他ではない。
                    # Union型のコンストラクタがエラーを投げても、それは単に無視する。
                    pass
        if not i:
            i = VoidSchema()
        if not o:
            o = VoidSchema()
        return FunctionType(i, o)

    def visit_binarytag(self, node):
        t = node.command.accept(self)
        return FunctionType(t.input_type, TagSchema(node.tag, t.output_type))

    def visit_unarytag(self, node):
        return FunctionType(VoidSchema(), TagSchema(node.tag, AnySchema()))

    def visit_each(self, node):
        self.namespaces.append({})
        try:
            t = node.cmd.accept(self)
            if node.prop:
                return FunctionType(ObjectSchema({}, wildcard=t.input_type), ObjectSchema({}, wildcard=t.output_type))
            else:
                return FunctionType(ArraySchema([t.input_type], {u'repeat': True}), 
                                    ArraySchema([t.output_type], {u'repeat': True}))
        finally:
            self.namespaces.pop(-1)

    def visit_time(self, node):
        self.namespaces.append({})
        try:
            return node.cmd.accept(self)
        finally:
            self.namespaces.pop(-1)

    def visit_take(self, node):
        self.namespaces.append({})
        try:
            t = node.cmd.accept(self)
            v = FunctionType(t.output_type, UnionSchema(BoolSchema(), TagSchema(u'True', AnySchema())))
            tc = TypeComparator(FunctionType(VoidSchema(), t.output_type), v)
            tc.compare()
            if tc.is_error:
                self.__messages.extend(tc.error_messages)
            return FunctionType(node.input_type, node.output_type, node.profile_container.type_var_names)
        finally:
            self.namespaces.pop(-1)

    def visit_script(self, node):
        o = self.namespaces 
        self.namespaces = [{}]
        try:
            return node.script.accept(self)
        finally:
            self.namespaces = o

OK = 0
ERROR = 1
SUSPICIOUS = 2

class TypeComparator(TreeCursor):
    def __init__(self, t1, t2):
        self.__stack = []
        self.__names = []
        self.type1 = t1
        self.type2 = t2
        self.__trace = []

    @property
    def type_vars(self):
        return self.type2.type_vars

    @property
    def is_error(self):
        for t, m in self.__trace:
            if t == ERROR:
                return True

    @property
    def is_suspicious(self):
        for t, m in self.__trace:
            if t == SUSPICIOUS:
                return True

    @property
    def error_messages(self):
        r = []
        for t, m in self.__trace:
            if t == ERROR:
                r.append(m)
        return r

    @property
    def warning_messages(self):
        r = []
        for t, m in self.__trace:
            if t == SUSPICIOUS:
                r.append(m)
        return r

    @property
    def messages(self):
        r = []
        for _, m in self.__trace:
            r.append(m)
        return r

    @property
    def input_type(self):
        return self.type1.input_type

    @property
    def output_type(self):
        return self.type2.output_type

    def _focus(self, obj):
        self.__stack.append(obj)
        return Cursor(self)

    def _shift(self):
        self.__stack.pop(-1)

    @property
    def primary_focused_dereference(self):
        assert len(self.__stack) > 0
        return self.__dereference(self.__stack[-1])

    @property
    def primary_focused(self):
        assert len(self.__stack) > 0
        return self.__stack[-1]

    def current_name(self, node):
        if len(self.__names) == 0:
            return  node.name
        return self.__names[-1]

    def __dereference(self, o):
        if isinstance(o, (NamedSchema, TypeReference)):
            return self.__dereference(o.body)
        else:
            return o

    def compare(self):
        lt = self.type1.output_type
        rt = self.type2.input_type
        self._focus(lt)
        rt.accept(self)

    def _sub(self, l, r):
        tc = TypeComparator(FunctionType(VoidSchema(), l), FunctionType(node, r))
        tc.compare()
        return tc

    def _visit_root(self, node):
        if not self.__names():
            self.__names.append(node.name)
        return node.body.accept(self)

    def _visit_scalar(self, node):
        p = self.primary_focused_dereference
        if node.type == u'void' or node.type == u'any':
            return
        elif isinstance(node, TypeVariable):
            res = self.type2.inference_type_var(node.name, p)
            if res: # 以前に推論した型変数と矛盾が生じた
                self.__trace.append((ERROR, u'{0} can not to assign to {1} (infered to {2})'.format(p.type, self.current_name(node), self.type2.type_vars[node.name])))
        elif isinstance(p, ScalarSchema):
            if p.type != node.type and (p.type != u'integer' and node.type != u'number'):
                self.__trace.append((ERROR, u'{0} ⊈ {1}'.foramt(self.primary_focused.name, self.current_name(node))))
            else:
                pass
        elif isinstance(p, UnionSchema):
            l = p.left
            r = p.right
            tc1 = TypeComparator(FunctionType(VoidSchema(), l), FunctionType(node, VoidSchema()))
            tc1.compare()
            tc2 = TypeComparator(FunctionType(VoidSchema(), r), FunctionType(node, VoidSchema()))
            tc2.compare()
            if tc1.is_error and tc2.is_error:
                self.__trace.append((ERROR, u'{0} ⊈ {1}'.format(self.dump(p), self.current_name(node))))
            else:
                for m in tc1.messages:
                    self.__trace.append((SUSPICIOUS, m))
                for m in tc2.messages:
                    self.__trace.append((SUSPICIOUS, m))
        elif isinstance(p, EnumSchema):
            m = []
            for v in p.enum:
                try:
                    node.validate(v)
                except:
                    m.append((SUSPICIOUS, u'{0} ⊈ {1}'.format(self.to_str(v), self.current_name(node))))
                else:
                    return
            self.__trace.append((ERROR, u'{0} ⊈ {1}'.format(self.dump(p), self.current_name(node))))
        else:
            self.__trace.append((ERROR, u'{0} ⊈ {1}'.format(self.primary_focused.name, self.current_name(node))))

    def _visit_option(self, node):
        p = self.primary_focused
        if not p.optional:
            self.__trace.append((SUSPICIOUS, u'%s ⊆ %s?' % (p.name, self.current_name(node))))
        node.body.accept(self)

    def _visit_enum(self, node):
        p = self.primary_focused_dereference
        if not isinstance(p, EnumSchema):
            self.__trace.append((ERROR, u'{0} ⊈ {1}'.format(self.primary_focused.name, self.dump(node))))
        e1 = p.enum
        e2 = node.enum
        if not set(e1).intersect(set(e2)):
            self.__trace.append((ERROR, u'{0} ∩ {1} is empty'.format(self.primary_focused.name, self.dump(node))))
        else:
            for e in e1:
                if e not in e2:
                    self.__trace.append((ERROR, u'{0} ⊈ {1}'.format(e, self.dump(node))))

    def _visit_object(self, node):
        p = self.primary_focused_dereference
        if not isinstance(p, ObjectSchema):
            self.__trace.append((ERROR, u'{0} ⊈ {1}'.format(self.primary_focused.name, self.current_name(node))))
        checked = set()
        for k, v in node.iteritems():
            self.__names.append(v.name)
            if not k in p and not v.optional:
                self.__trace.append((ERROR, u'{0} ⊈ {1}'.format(k, self.primary_focused.name)))
            else:
                with self._focus(p[k]):
                    v.accept(self)
            checked.add(k)
            self.__names.pop(-1)
        for k, v in p.iteritems():
            if k in checked:
                continue
            if k not in node:
                tc = self._sub(v, node.wildcard)
                if tc.is_error:
                    if v.optional:
                        self.__trace.append((SUSPICIOUS, u'{0} ⊈ {1}'.format(k, self.current_name(node.wildcard))))
                    else:
                        self.__trace.append((ERROR, u'{0} ⊈ {1}'.format(k, node.name)))
            else:
                with self._focus(v):
                    node[k].accept(self)
        with self._focus(p.wildcard):
            node.wildcard.accept(self)

    def _visit_array(self, node):
        p = self.primary_focused_dereference
        if not isinstance(p, ArraySchema):
            self.__trace.append((ERROR, u'{0} ⊈ {1}'.format(self.primary_focused.name, self.current_name(node))))
        for i, s in enumerate(node):
            self.__names.append(s.name)
            if len(p) < i:
                if not p.repeat:
                    self.__trace.append((ERROR, u'{0} ⊈ {1}'.format(self.primary_focused.name, self.current_name(node))))
                else:
                    with self._focus(p.schema_list[-1]):
                        s.accept(self)
            else:
                with self._focus(p.schema_list[i]):
                    s.accept(self)
            self.__names.pop(-1)
        for i, s in enumerate(p):
            if len(node) < i:
                if not p.repeat:
                    self.__trace.append((ERROR, u'{0} ⊈ {1}'.format(self.primary_focused.name, self.current_name(node))))
                else:
                    with self._focus(s):
                        node.schema_list[-1].accept(self)

    def _visit_bag(self, node):
        pass

    def _visit_union(self, node):
        p = self.primary_focused_dereference
        if isinstance(p, UnionSchema):
            pass

    def _visit_tag(self, node):
        p = self.primary_focused_dereference
        if node.tag == '*':
            return
        elif node.tag == '*!':
            if p.tag in _builtin_tags:
                self.__trace.append((ERROR, u'{0} ⊈ {1}'.format(self.primary_focused.name, self.current_name(node))))
        elif node.tag != p.tag:
            self.__trace.append((ERROR, u'{0} ⊈ {1}'.format(self.primary_focused.name, self.current_name(node))))

    def dump(self, n):
        return n.accept(MiniDumper())

    def to_str(self, n):
        return MiniDumper()._to_str(n)

_builtin_tags = [
    'integer',
    'number',
    'string',
    'binary',
    'boolean',
    'array',
    'object',
    'any',
    'null',
    'void',
    'never',
    'enum',
    ]

class Cursor(object):
    def __init__(self, state):
        self.state = state

    def __enter__(self):
        pass
        #self.state._focus(self.state.primary_focused_dereference)

    def __exit__(self, exc_type, exc_value, traceback):
        self.state._shift()
        return True

class FunctionType(object):
    u"""
    型変数、入力型、出力型の三つ組。
    """
    def __init__(self, input_type, output_type, type_var_names=list()):
        self.type_vars = {}
        if isinstance(type_var_names, dict):
            self.type_vars.update(type_var_names)
        else:
            for k in type_var_names:
                self.type_vars[k] = None
        self.input_type = input_type
        self.output_type = output_type

    def inference_type_var(self, name, type):
        if self.type_vars[name] is None:
            self.type_vars[name] = type
        else:
            old = self.type_vars[name]
            tc = TypeComparator(FunctionType(VoidSchema(), old), FunctionType(type, VoidSchema()))
            tc.compare()
            if tc.is_error:
                return tc
            else:
                self.type_vars[name] = type

