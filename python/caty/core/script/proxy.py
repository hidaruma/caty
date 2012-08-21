#coding:utf-8
from caty.core.command import *
from caty.core.script.node import *
from caty.core.script.builder import CommandCombinator, DiscardCombinator
from caty.core.exception import InternalException, throw_caty_exception
import caty.jsontools as json

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

    def reify(self):
        return json.tagged(self.reification_type, self._reify())

    def _reify(self):
        raise NotImplemtentedError(u'{0}.reify'.format(self.__class__.__name__))

class CommandProxy(Proxy):
    u"""コマンド呼び出しに遭遇したときに構築されるプロキシクラス。
    """
    reification_type = u'_call'

    def __init__(self, name, type_args, opts, args, pos):
        self.name = name
        self.opts = opts
        self.args = args
        self.type_args = type_args
        self.module = None
        self.pos = pos

    def set_module(self, module):
        self.module = module

    def instantiate(self, builder):
        return builder.build(self, self.type_args, self.opts, self.args, self.pos, self.module)

    def _reify(self):
        return {
            'name': self.name,
            'opts': [o.reify() for o in self.opts],
            'args': [o.reify() for o in self.args],
            'typeArgs': self.type_args,
            'pos': self.pos,
        }

class ScalarProxy(Proxy):
    reification_type = u'_scalar'
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

    def _reify(self):
        return self.value

class ListProxy(Proxy):
    reification_type = u'_list'
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

    def _reify(self):
        return [v.reify() for v in self.values]

class ObjectProxy(Proxy):
    reification_type = u'_object'
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

    def _reify(self):
        o = {}
        for n in self.nodes:
            o[n.name] = n.reify()
        return o

class ConstNodeProxy(Proxy):
    def __init__(self, n, v):
        self.name = n
        self.value = v

    def instantiate(self, builder):
        return ConstNode(self.name, self.value)

    def set_module(self, module):
        pass

    def reify(self):
        return json.tagged(u'_scalar', self.value)

class CommandNodeProxy(Proxy):
    def __init__(self, n, c):
        self.name = n
        self.cmdproxy = c

    def instantiate(self, builder):
        return CommandNode(self.name, self.cmdproxy.instantiate(builder))

    def set_module(self, module):
        self.cmdproxy.set_module(module)

    def reify(self):
        return self.cmdproxy.reify()

class DispatchProxy(Proxy):
    reification_type = u'_when'
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

    def _reify(self):
        return {
            'opts': [o.reify() for o in self.opts],
            'cases': [c.reify() for c in self.cases]
        }

class TypeCaseProxy(Proxy):
    reification_type = u'_case'
    def __init__(self, path, via):
        self.cases = []
        self.path = path
        self.via = via

    def add_case(self, case):
        self.cases.append(case)

    def instantiate(self, builder):
        if self.via:
            via = self.via.instantiate(builder)
        else:
            via = None
        t = TypeCase(self.path, via)
        for c in self.cases:
            t.add_case(c.instantiate(builder))
        return t

    def set_module(self, module):
        if self.via:
            self.via.set_module(module)
        for c in self.cases:
            c.set_module(module)
        import operator
        from caty.core.casm.language.schemaparser import Annotations
        from caty.core.schema.base import NamedSchema
        types = [c.type for c in self.cases if c.typedef != u'*']
        for t1, t2 in [(t1, t2) for t1 in types for t2 in types]:
            if t1 != t2:
                x = NamedSchema(u'', [], t1 & t2, module)
                tn = module.make_type_normalizer()
                try:
                    n = x.accept(tn)
                except:
                    pass
                else:
                    throw_caty_exception('CompileError', module._app.i18n.get(u'types are not exclusive: $type1, $type2', type1=module.make_dumper().visit(t1), type2=module.make_dumper().visit(t2)))

    def _reify(self):
        o = {
            'cases': [c.reify() for c in self.cases]
        }
        if self.path:
            p = self.path._to_str()
            o['path'] = unicode(p) if not isinstance(p, unicode) else p
        if self.via:
            o['via'] = self.via.reify()
        return o

class TypeCondProxy(Proxy):
    reification_type = u'_cond'
    def __init__(self, path):
        self.cases = []
        self.path = path

    def add_case(self, case):
        self.cases.append(case)

    def instantiate(self, builder):
        t = TypeCase(self.path, None)
        for c in self.cases:
            t.add_case(c.instantiate(builder))
        return t

    def set_module(self, module):
        for c in self.cases:
            c.set_module(module)

    def _reify(self):
        o = {
            'cases': [c.reify() for c in self.cases]
        }
        if self.path:
            p = self.path._to_str()
            o['path'] = unicode(p) if not isinstance(p, unicode) else p
        return o

class BranchProxy(Proxy):
    def __init__(self, typedef, cmdproxy):
        self.typedef = typedef
        self.cmdproxy = cmdproxy
        self.type = None

    def set_module(self, module):
        self.cmdproxy.set_module(module)
        if self.typedef == u'*': return
        from caty.core.casm.language.schemaparser import ASTRoot, Annotations
        ar = ASTRoot(u'', [], self.typedef, Annotations([]), u'')
        sb = module.make_schema_builder()
        rr = module.make_reference_resolver()
        cd = module.make_cycle_detecter()
        ta = module.make_typevar_applier()
        tn = module.make_type_normalizer()
        self.type = ar.accept(sb).accept(rr).accept(cd).accept(ta).accept(tn).body

    def instantiate(self, builder):
        return Branch(self.type, self.cmdproxy.instantiate(builder))
        
    def reify(self):
        return {
            'type': self.typedef.reify() if self.typedef != u'*' else json.TagOnly(u'_wildcard'),
            'body': self.cmdproxy.reify()
        }
    
class TagProxy(Proxy):
    reification_type = u'_tag'
    def __init__(self, t, c):
        self.tag = t
        self.cmdproxy = c

    def instantiate(self, builder):
        return TagBuilder(self.tag, self.cmdproxy.instantiate(builder))

    def set_module(self, module):
        self.cmdproxy.set_module(module)

    def _reify(self):
        return {
            'tag': self.tag,
            'value': self.cmdproxy.reify()
        }

class UnaryTagProxy(Proxy):
    reification_type = u'_unaryTag'
    def __init__(self, t):
        self.tag = t

    def instantiate(self, builder):
        return UnaryTagBuilder(self.tag)

    def set_module(self, module):
        pass

    def _reify(self):
        return {
            'tag': self.tag
        }

class CaseProxy(TagProxy):
    def instantiate(self, builder):
        return Case(self.tag, self.cmdproxy.instantiate(builder))

class UntagCaseProxy(TagProxy):
    reification_type = u'_untag'
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

    def _reify(self):
        return {
            'opts': [o.reify() for o in self.opts],
            'body': self.cmdproxy.reify()
        }

class EachProxy(FunctorProxy):
    reification_type = u'_each'
    def _get_class(self):
        return Each

class TakeProxy(FunctorProxy):
    reification_type = u'_take'
    def _get_class(self):
        return Take

class TimeProxy(FunctorProxy):
    reification_type = u'_time'
    def _get_class(self):
        return Time

class StartProxy(FunctorProxy):
    reification_type = u'_start'
    def _get_class(self):
        return Start

class BeginProxy(FunctorProxy):
    reification_type = u'_begin'
    def _get_class(self):
        return Begin

class RepeatProxy(Proxy):
    def instantiate(self, builder):
        return Repeat()

    def set_module(self, module):
        pass

    def reify(self):
        return TagOnly(u'_repeat')

class CombinatorProxy(Proxy):
    def __init__(self, a, b):
        self.a = a
        self.b = b
        self.reification_type = u'_pipe' if not isinstance(self.b, DiscardProxy) else u'_discard'

    def instantiate(self, builder):
        if isinstance(self.b, DiscardProxy):
            return DiscardCombinator(self.a.instantiate(builder), self.b.instantiate(builder))
        else:
            return CommandCombinator(self.a.instantiate(builder), self.b.instantiate(builder))

    def set_module(self, module):
        self.a.set_module(module)
        self.b.set_module(module)

    def _reify(self):
        return [self.a.reify(), self.b.reify()]

class VarStoreProxy(CommandProxy):
    reification_type = u'_store'
    def __init__(self, name):
        self.name = name

    def instantiate(self, builder):
        return VarStore(self.name)

    def set_module(self, module):
        pass

    def _reify(self):
        return {
            'name': self.name
        }

class VarRefProxy(CommandProxy):
    reification_type = u'_varref'
    def __init__(self, name, optional, default):
        self.name = name
        self.optional = optional
        self.default = default

    def instantiate(self, builder):
        return VarRef(self.name, self.optional, self.default)

    def set_module(self, module):
        pass

    def _reify(self):
        return {
            'name': self.name,
            'optional': self.optional
        }

class ArgRefProxy(CommandProxy):
    reification_type = u'_argref'
    def __init__(self, name, optional):
        self.name = name
        self.optional = optional

    def instantiate(self, builder):
        return ArgRef(self.name, self.optional)

    def set_module(self, module):
        pass

    def _reify(self):
        return {
            'name': self.name,
            'optional': self.optional
        }

class DiscardProxy(Proxy):
    def __init__(self, target):
        self.target = target

    def instantiate(self, builder):
        return self.target.instantiate(builder)
    
    def set_module(self, module):
        self.target.set_module(module)

    def reify(self):
        return self.target.reify()

class FragmentProxy(Proxy):
    reification_type = u'_fragment'
    def __init__(self, c, fragment_name):
        self.cmdproxy = c
        self.fragment_name = fragment_name

    def instantiate(self, builder):
        r = PipelineFragment(self.cmdproxy.instantiate(builder), self.fragment_name)
        builder.set_facility_to(r)
        return r

    def set_module(self, module):
        self.cmdproxy.set_module(module)

    def _reify(self):
        return {
            'name': self.fragment_name,
            'body': self.cmdproxy.reify()
        }   

class EnvelopeProxy(Proxy):
    def __init__(self, c):
        self.cmdproxy = c

    def instantiate(self, builder):
        r = ActionEnvelope(self.cmdproxy.instantiate(builder))
        return r

    def set_module(self, module):
        self.cmdproxy.set_module(module)

    def reify(self):
        return None #throw_caty_exception('RuntimeError', u'Action command can not reified by inspect:reify-cmd')

class JsonPathProxy(Proxy):
    reification_type = u'_jsonPath'
    def __init__(self, stm, pos):
        self.stm = stm
        self.pos = pos

    def set_module(self, module):
        self.module = module

    def instantiate(self, builder):
        return JsonPath(self.stm, self.pos)

    def _reify(self):
        p = self.stm._to_str()
        return {
            'path': unicode(p) if not isinstance(p, unicode) else p,
            'pos': self.pos
        }

def combine_proxy(args):
    return reduce(CombinatorProxy, args)




