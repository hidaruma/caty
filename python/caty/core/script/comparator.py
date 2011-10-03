# coding: utf-8
from caty.core.schema import *
from caty.core.script.builder import CommandCombinator
from caty.core.script.interpreter import BaseInterpreter
from caty.core.script.node import *
from caty.core.command import ScriptWrapper
from caty.core.std.command.builtin import Void
from caty.core.typeinterface import TreeCursor
import caty.jsontools as json

class PipeLineComparator(BaseInterpreter):
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
        self.__trace = []

    def find_name(self, name):
        for n in reversed(self.namespaces):
            if name in n:
                return n[name]
        return TypeVariable(name, [], {}, None)

    def visit_command(self, node):
        return FunctionType(node.in_schema, node.out_schema, node.profile_container.type_var_names)

    def visit_pipe(self, node):
        a = node.bf.accept(self)
        b = node.af.accept(self)
        tc = TypeComparator(a, b)
        r = tc.compare()
        if isinstance(node.af, VarStore):
            self.namespaces[-1][node.af.var_name] = r.output_type
        return r

    def visit_discard_pipe(self, node):
        a = node.bf.accept(self)
        b = node.af.accept(self)
        return b

    def visit_scalar(self, node):
        return FunctionType(VoidSchema(), EnumSchema([node.value]), [])

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
                else:
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
            if tc.error:
                self.__trace.append(tc.message)
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

class TypeComparator(TreeCursor):
    def __init__(self, t1, t2):
        self.__stack = []
        self.type1 = t1
        self.type2 = t2
        self.error = False
        self.message = u''

    def _focus(self, obj):
        self.__stack.append(obj)
        return Cursor(self)

    def _shift(self):
        self.__stack.pop(-1)

    @property
    def primary_focused(self):
        assert len(self.__stack) > 0
        return sefl.__stack[-1]

    def compare(self):
        if self.type1.name != self.type2.name:
            self.error = True
            self.message = u'%s != %s' % (self.type1.name, self.type2.name)
        #lt = self.type1.output_type
        #rt = self.type2.input_type
        #self._focus(lt)
        #rt.accept(self)


class Cursor(object):
    def __init__(self, state):
        self.state = state

    def __enter__(self):
        return self.state.primary_focused

    def __exit__(self, exc_type, exc_value, traceback):
        self.state._shift()
        return True

class FunctionType(object):
    u"""
    型変数、入力型、出力型の三つ組。
    """
    def __init__(self, input_type, output_type, type_var_names):
        self.type_vars = {}
        for k in type_var_names:
            self.type_vars[k] = AnySchema()
        self.input_type = input_type
        self.output_type = output_type

    def inference_type_var(self, varname, type):
        pass


