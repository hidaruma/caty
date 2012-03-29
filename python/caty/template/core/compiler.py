# coding: utf-8
from caty.template.core.st import *
from caty.template.core.instructions import *
import caty
class Compiler(object):
    u"""バイトコードコンパイラ。
    このクラス自体は抽象クラスであり、適宜サブクラス化して使う。
    サブクラスでは構文木の生成を必ず実装しなければならず、
    また必要に応じてオブジェクトコードコンパイラも定義すること。
    前者は build_st を、後者は object_code_generator をそれぞれ
    オーバーライドすることで行う。
    """
    
    def compile(self, fo):
        t = self.build_st(fo)
        v = self.object_code_generator()
        code = tuple(v.visit(t))
        return code

    def build_st(self, fo):
        raise NotImplementedError

    def object_code_generator(self):
        return ObjectCodeGenerator()
    
class STVistor(object):
    def __init__(self):
        self.dispatch_mapping = {
            Template: self.template,
            String: self.string,
            If: self.if_,
            Elif: self.elif_,
            Else: self.else_,
            For: self.for_,
            Include: self.include,
            VarLoad: self.varload,
            FilterCall: self.filter,
            VarDisp: self.vardisp,
            Null: self.null,
            DefMacro: self.def_macro,
            ExpandMacro: self.expand_macro,
            DefFunc :self.def_func,
            CallFunc: self.call_func,
            DefGroup: self.def_group,
            CallGroup: self.call_group,
        }

    def visit(self, node):
        for c in self.dispatch_mapping[type(node)](node):
            yield c

    def template(self, node):
        for n in node.nodes:
            for c in n.accept(self):
                yield c

    def string(self, node):
        yield (STRING, node.data)
        
    def if_(self, node):
        raise NotImplementedError
    
    def elif_(self, node):
        raise NotImplementedError
    
    def else_(self, node):
        raise NotImplementedError

    def for_(self, node):
        raise NotImplementedError

    def include(self, node):
        raise NotImplementedError

    def varload(self, node):
        raise NotImplementedError

    def filter(self, node):
        raise NotImplementedError

    def vardisp(self, node):
        raise NotImplementedError

    def null(self, node):
        if False: yield

    def def_macro(self, node):
        raise NotImplementedError

    def expand_macro(self, node):
        raise NotImplementedError

    def def_func(self, node):
        raise NotImplementedError

    def call_func(self, node):
        raise NotImplementedError

    def def_group(self, node):
        raise NotImplementedError

    def call_group(self, node):
        raise NotImplementedError

class ObjectCodeGenerator(STVistor):
    def __init__(self):
        STVistor.__init__(self)
        self.label_stack = []
        self.group_label = {}
        self.current_namespace = []
        self.defined_groups = set()

    def if_(self, node):
        else_label = self.create_label(node)
        end_label = else_label + 'end'
        for c in node.varnode.accept(self):
            yield c
        yield (JMPUNLESS, else_label)
        for c in node.subtempl.accept(self):
            yield c
        yield (JMP, end_label)
        yield (LABEL, else_label)
        for elifnode in node.elifnodes:
            assert isinstance(elifnode, (Null, Elif))
            elifnode.upcoming_end_label = end_label
            for c in elifnode.accept(self):
                yield c
        for c in node.elsenode.accept(self):
            yield c
        yield (LABEL, end_label)

    def elif_(self, node):
        assert node.upcoming_end_label != None
        else_label = self.create_label(node)
        for c in node.varnode.accept(self):
            yield c
        yield (JMPUNLESS, else_label)
        for c in node.subtempl.accept(self):
            yield c
        yield (JMP, node.upcoming_end_label)
        yield (LABEL, else_label)

    def else_(self, node):
        for c in node.subtempl.accept(self):
            yield c

    def for_(self, node):
        label = self.create_label(node)
        end_label = label + 'end'
        else_label = self.create_label(node.elsetempl)
        
        # ループ用コンテキストの用意
        yield (NEWCTX, None)
        yield (PUSH, -1)
        yield (CPUSH, node.index)
        yield (PUSH, 0)
        yield (CPUSH, node.iteration)
        for c in node.varnode.accept(self):
            yield c
        yield (ENUM, None)
        yield (CPUSH, node.context)
        yield (LOAD, node.context)
        yield (LEN, None)
        yield (CPUSH, node.counter)

        # ループアイテムの要素数がゼロの場合即ループ終了、 else 節へ
        yield (LOAD, node.counter)
        yield (PUSH, 0)
        yield (LT, None)
        yield (NOT, None)
        yield (JMPUNLESS, else_label)

        # ループの先頭位置
        yield (LABEL, label)
        
        # ループ回数のカウントアップ
        yield (LOAD, node.index)
        yield (PUSH, 1)
        yield (ADD, None)
        yield (CPUSH, node.index)

        yield (LOAD, node.iteration)
        yield (PUSH, 1)
        yield (ADD, None)
        yield (CPUSH, node.iteration)

        # 先頭要素かどうかの判断
        yield (PUSH, 1)
        yield (LOAD, node.iteration)
        yield (EQ, None)
        yield (CPUSH, node.first)

        # 末尾要素かどうかの判断
        yield (LOAD, node.iteration)
        yield (LOAD, node.counter)
        yield (EQ, None)
        yield (CPUSH, node.last)

        # ループキーの割り当て
        yield (LOAD, node.context)
        yield (LOAD, node.index)
        yield (AT, None)
        yield (PUSH, 0)
        yield (AT, None)
        yield (CPUSH, node.loopkey)

        # ループアイテムの割り当て
        yield (LOAD, node.context)
        yield (LOAD, node.index)
        yield (AT, None)
        yield (PUSH, 1)
        yield (AT, None)
        yield (CPUSH, node.loopitem)

        # サブテンプレートの展開
        for c in node.subtempl.accept(self):
            yield c

        # ループを続けるか否かの判断
        yield (CDEL, node.loopitem)
        yield (LOAD, node.last)
        yield (JMPUNLESS, label)
        yield (JMP, end_label)
        
        # else 節
        yield (LABEL, else_label)
        for c in node.elsetempl.accept(self):
            yield c

        # ループを抜けたあとの処理
        yield (LABEL, end_label)
        yield (DELCTX, None)

    def include(self, node):
        yield (SUBCONTEXT, node.context)
        yield (INCLUDE, node.filename)

    def varload(self, node):
        if node.undefinable:
            undef_label = self.create_label(node)
            end_label = self.create_label(node)
            yield (DEFINED, node.varname)
            yield (JMPUNLESS, undef_label)
            yield (LOAD, node.varname)
            yield (JMP, end_label)
            yield (LABEL, undef_label)
            yield (PUSH, caty.UNDEFINED)
            yield (LABEL, end_label)
        else:
            yield (LOAD, node.varname)

    def filter(self, node):
        l = len(node.args)
        for a in node.args:
            yield (PUSH, a)
        yield (CALL, [node.name, l+1]) # スタック上の値も含むため

    def vardisp(self, node):
        yield (POP, None)

    def create_label(self, obj):
        label = str(id(obj))
        while label in self.label_stack:
            label += 'x'
        self.label_stack.append(label)
        return label

    def def_macro(self, node):
        yield (MACRO, node.name)
        for k, v in node.vars:
            skip_label = self.create_label(node)
            yield (DEFINED, k)
            yield (NOT, None)
            yield (JMPUNLESS, skip_label)
            yield (PUSH, v)
            yield (CPUSH, k)
            yield (LABEL, skip_label)
        for c in node.sub_template.accept(self):
            yield c
        yield (RETURN, None)

    def expand_macro(self, node):
        yield (NEWCTX, None)
        for k, v in node.args:
            yield (LOAD, v)
            yield (CPUSH, k)
        yield (EXPAND, node.name)
        yield (DELCTX, None)

    def def_func(self, node):
        skip_label = self.create_label(node)
        yield (FUNCTION_MATCH, '.'.join(self.current_namespace))
        yield (DISPATCH, node.match)
        yield (SWAP, None)
        yield (DISCARD, None)
        yield (JMPUNLESS, skip_label)
        yield (FUNCTION_DEF, '.'.join(self.current_namespace + [node.name]))
        if node.match:
            yield (DISPATCH, node.match)
            yield (JMPUNLESS, skip_label)
        elif node.context_type:
            yield (VALIDATE, node.context_type)
        else:
            raise
        yield (SWAP, None)
        yield (MASK_CONTEXT, None)
        yield (CPUSH, node.matched)
        for c in node.sub_template.accept(self):
            yield c
        yield (UNMASK_CONTEXT, None)
        yield (RETURN, None)
        yield (LABEL, skip_label)

    def call_func(self, node):
        for o in node.context.accept(self):
            yield o
        yield (CALL_TEMPLATE, node.name)

    def def_group(self, node):
        if node.name is not None:
            name = '.'.join(self.current_namespace + [node.name])
            yield (GROUP_DEF, '.'.join(self.current_namespace + [node.name]))
            self.current_namespace.append(node.name)
        else:
            name = u''
            yield (GROUP_DEF, u'')
        if name in self.defined_groups:
            raise Exception('%s is already defined' % name)
        else:
            self.defined_groups.add(name)
        for m in node.member:
            for o in m.accept(self):
                yield o
        if node.name is not None:
            self.current_namespace.pop(-1)
        yield (END_GROUP, None)

    def call_group(self, node):
        for o in node.context.accept(self):
            yield o
        yield (CALL_GROUP, node.name if node.name else u'')

class STDebugger(STVistor):
    def template(self, node):
        yield node.type
        for n in node.nodes:
            for c in n.accept(self):
                yield c

    def string(self, node):
        yield node.type
        
    def if_(self, node):
        yield node.type
        for t in node.varnode.accept(self):
            yield t
        for t in node.subtempl.accept(self):
            yield t
        for t in node.elifnode.accept(self):
            yield t
        for t in node.elsenode.accept(self):
            yield t

    def elif_(self, node):
        yield node.type
        for t in node.varnode.accept(self):
            yield t
        for t in node.subtempl.accept(self):
            yield t
    
    def else_(self, node):
        yield node.type
        for t in node.subtempl.accept(self):
            yield t

    def for_(self, node):
        yield node.type
        for t in node.varnode.accept(self):
            yield t
        for t in node.subtempl.accept(self):
            yield t
        for t in node.elsetempl.accept(self):
            yield t

    def include(self, node):
        yield node.type

    def varload(self, node):
        yield node.type

    def filter(self, node):
        yield node.type

    def vardisp(self, node):
        yield node.type

    def null(self, node):
        yield node.type


