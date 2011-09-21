#coding:utf-8
from caty.core.command import *
from caty.core.script.node import *
from caty.core.script.builder import CommandCombinator, DiscardCombinator
from caty.core.exception import InternalException

class Proxy(object):
    u"""パイプライン構築のためのプロキシ。
    テスタビリティの確保と構文エラー発見容易性のために、
    パイプラインの構築の際にはプロキシクラスを間に挟み、遅延初期化を行う。
    基本的に caty.shell.script.node モジュールのクラスとプロキシは一対一対応する。
    プロキシと本体はコマンドオブジェクト独自のメソッド・プロパティを除いては
    ソースコード上で見えるメソッド・プロパティが一致している。
    """
    def instantiate(self, builder):
        raise NotImplemtentedError

    def set_module(self, module):
        pass

class CommandProxy(Proxy):
    u"""コマンド呼び出しに遭遇したときに構築されるプロキシクラス。
    """
    def __init__(self, name, type_args, opts, args):
        self.name = name
        self.opts = opts
        self.args = args
        self.type_args = type_args
        self.module = None

    def set_module(self, module):
        self.module = module

    def instantiate(self, builder):
        return builder.build(self, self.type_args, self.opts, self.args)

class ScalarProxy(Proxy):
    def __init__(self):
        self.value = None

    def __call__(self):
        import traceback
        for l in traceback.format_stack(): print l

    def set_value(self, v):
        self.value = v

    def instantiate(self, builder):
        s = ScalarBuilder()
        s.set_value(self.value)
        return s

    def set_module(self, module):
        pass

class ListProxy(Proxy):
    def __init__(self):
        self.values= []
    
    def set_values(self, values):
        self.values = values

    def instantiate(self, builder):
        l = ListBuilder()
        l.set_values([v.instantiate(builder) for v in self.values])
        return l

    def set_module(self, module):
        for v in self.values:
            v.set_module(module)

class ObjectProxy(Proxy):
    def __init__(self):
        self.nodes = []

    def add_node(self, node):
        self.nodes.append(node)

    def instantiate(self, builder):
        o = ObjectBuilder()
        for n in self.nodes:
            o.add_node(n.instantiate(builder))
        return o

    def set_module(self, module):
        for n in self.nodes:
            n.set_module(module)

class ConstNodeProxy(Proxy):
    def __init__(self, n, v):
        self.name = n
        self.value = v

    def instantiate(self, builder):
        return ConstNode(self.name, self.value)

    def set_module(self, module):
        pass

class CommandNodeProxy(Proxy):
    def __init__(self, n, c):
        self.name = n
        self.cmdproxy = c

    def instantiate(self, builder):
        return CommandNode(self.name, self.cmdproxy.instantiate(builder))

    def set_module(self, module):
        self.cmdproxy.set_module(module)

class DispatchProxy(Proxy):
    def __init__(self, opts):
        self.cases = []
        self.opts = opts

    def add_case(self, case):
        self.cases.append(case)

    def instantiate(self, builder):
        d = Dispatch()
        for c in self.cases:
            d.add_case(c.instantiate(builder))
        return d

    def set_module(self, module):
        for c in self.cases:
            c.set_module(module)

class TagProxy(Proxy):
    def __init__(self, t, c):
        self.tag = t
        self.cmdproxy = c

    def instantiate(self, builder):
        return TagBuilder(self.tag, self.cmdproxy.instantiate(builder))

    def set_module(self, module):
        self.cmdproxy.set_module(module)

class UnaryTagProxy(Proxy):
    def __init__(self, t):
        self.tag = t

    def instantiate(self, builder):
        return UnaryTagBuilder(self.tag)

    def set_module(self, module):
        pass

class CaseProxy(TagProxy):
    def instantiate(self, builder):
        return Case(self.tag, self.cmdproxy.instantiate(builder))

class UntagCaseProxy(TagProxy):
    def instantiate(self, builder):
        return UntagCase(self.tag, self.cmdproxy.instantiate(builder))

class FunctorProxy(Proxy):
    def __init__(self, c, opts):
        self.cmdproxy = c
        self.opts = opts

    def instantiate(self, builder):
        r = self._get_class()(self.cmdproxy.instantiate(builder), self.opts)
        builder.set_facility_to(r)
        return r

    def set_module(self, module):
        self.cmdproxy.set_module(module)

class EachProxy(FunctorProxy):
    def _get_class(self):
        return Each

class TakeProxy(FunctorProxy):
    def _get_class(self):
        return Take

class TimeProxy(FunctorProxy):
    def _get_class(self):
        return Time

class CombinatorProxy(Proxy):
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def instantiate(self, builder):
        if isinstance(self.b, DiscardProxy):
            return DiscardCombinator(self.a.instantiate(builder), self.b.instantiate(builder))
        else:
            return CommandCombinator(self.a.instantiate(builder), self.b.instantiate(builder))

    def set_module(self, module):
        self.a.set_module(module)
        self.b.set_module(module)

class VarStoreProxy(CommandProxy):
    def __init__(self, name):
        self.name = name

    def instantiate(self, builder):
        return VarStore(self.name)

    def set_module(self, module):
        pass

class VarRefProxy(CommandProxy):
    def __init__(self, name, optional):
        self.name = name
        self.optional = optional

    def instantiate(self, builder):
        return VarRef(self.name, self.optional)

    def set_module(self, module):
        pass

class ArgRefProxy(CommandProxy):
    def __init__(self, name, optional):
        self.name = name
        self.optional = optional

    def instantiate(self, builder):
        return ArgRef(self.name, self.optional)

    def set_module(self, module):
        pass

class DiscardProxy(Proxy):
    def __init__(self, target):
        self.target = target

    def instantiate(self, builder):
        return self.target.instantiate(builder)
    
    def set_module(self, module):
        self.target.set_module(module)

class FragmentProxy(Proxy):
    def __init__(self, c, fragment_name):
        self.cmdproxy = c
        self.fragment_name = fragment_name

    def instantiate(self, builder):
        r = PipelineFragment(self.cmdproxy.instantiate(builder), self.fragment_name)
        builder.set_facility_to(r)
        return r

    def set_module(self, module):
        self.cmdproxy.set_module(module)

def combine_proxy(args):
    return reduce(CombinatorProxy, args)




