#coding:utf-8
from caty.core.spectypes import UNDEFINED
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
        raise NotImplementedError

    def set_module(self, module):
        pass

    def update_module(self, module):
        pass
        
    def reify(self):
        return json.tagged(self.reification_type, self._reify())

    def _reify(self):
        raise NotImplementedError(u'{0}.reify'.format(self.__class__.__name__))

    def clone(self):
        raise NotImplementedError(u'{0}.clone'.format(self.__class__.__name__))

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

    def clone(self):
        new = CommandProxy(self.name, self.type_args[:], self.opts, self.args, self.pos)
        return new

    def set_module(self, module):
        self.module = module

    def update_module(self, module):
        if self.module and module and self.module.canonical_name == module.canonical_name:
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

    def accept(self, visitor):
        visitor._visit_command(self)

class ScalarProxy(Proxy):
    reification_type = u'_scalar'
    def __init__(self):
        self.value = None

    def clone(self):
        new = ScalarProxy()
        new.value = self.value
        return new

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

    def accept(self, visitor):
        pass

class ListProxy(Proxy):
    reification_type = u'_list'
    def __init__(self):
        self.values= []
    
    def clone(self):
        new = ListProxy()
        new.values = [v.clone() for v in self.values]
        return new

    def set_values(self, values):
        self.values = values

    def instantiate(self, builder):
        l = ListBuilder()
        l.set_values([v.instantiate(builder) for v in self.values])
        return l

    def set_module(self, module):
        for v in self.values:
            v.set_module(module)

    def update_module(self, module):
        for v in self.values:
            v.update_module(module)

    def _reify(self):
        return [v.reify() for v in self.values]

    def accept(self, visitor):
        for v in self.values:
            v.accept(visitor)

class ParallelListProxy(ListProxy):
    def clone(self):
        new = ParallelListProxy()
        new.values = [v.clone() for v in self.values]
        new.wildcard = self.wildcard
        return new

    def set_wildcard(self, wildcard):
        self.wildcard = wildcard

    def instantiate(self, builder):
        l = ParallelListBuilder()
        l.set_values([v.instantiate(builder) for v in self.values])
        l.wildcard = self.wildcard
        return l

    def accept(self, visitor):
        for v in self.values:
            v.accept(visitor)

class ObjectProxy(Proxy):
    reification_type = u'_object'
    def __init__(self):
        self.nodes = []

    def clone(self):
        new = ObjectProxy()
        for n in self.nodes:
            new.add_node(n.clone())
        return new

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

    def update_module(self, module):
        for n in self.nodes:
            n.update_module(module)

    def _reify(self):
        o = {}
        for n in self.nodes:
            o[n.name] = n.reify()
        return o

    def accept(self, visitor):
        for n in self.nodes:
            n.accept(visitor)

class ParallelObjectProxy(Proxy):
    reification_type = u'_object'
    def __init__(self):
        self.nodes = []

    def clone(self):
        new = ParallelObjectProxy()
        for n in self.nodes:
            new.add_node(n.clone())
        return new

    def add_node(self, node):
        self.nodes.append(node)

    def instantiate(self, builder):
        o = ParallelObjectBuilder()
        for n in self.nodes:
            o.add_node(n.instantiate(builder))
        return o

    def set_module(self, module):
        for n in self.nodes:
            n.set_module(module)

    def update_module(self, module):
        for n in self.nodes:
            n.update_module(module)

    def _reify(self):
        o = {}
        for n in self.nodes:
            o[n.name] = n.reify()
        return o

    def accept(self, visitor):
        for n in self.nodes:
            n.accept(visitor)

class ConstNodeProxy(Proxy):
    def __init__(self, n, v):
        self.name = n
        self.value = v

    def clone(self):
        return ConstNodeProxy(self.name, self.value)

    def instantiate(self, builder):
        return ConstNode(self.name, self.value)

    def set_module(self, module):
        pass

    def reify(self):
        return json.tagged(u'_scalar', self.value)

    def accept(self, visitor):
        pass

class CommandNodeProxy(Proxy):
    def __init__(self, n, c):
        self.name = n
        self.cmdproxy = c

    def clone(self):
        return CommandNodeProxy(self.name, self.cmdproxy.clone())

    def instantiate(self, builder):
        return CommandNode(self.name, self.cmdproxy.instantiate(builder))

    def set_module(self, module):
        self.cmdproxy.set_module(module)

    def update_module(self, module):
        self.cmdproxy.update_module(module)

    def reify(self):
        return self.cmdproxy.reify()


    def accept(self, visitor):
        self.cmdproxy.accept(visitor)

class DispatchProxy(Proxy):
    reification_type = u'_when'
    def __init__(self, opts):
        self.cases = []
        self.opts = opts

    def clone(self):
        new = DispatchProxy(self.opts)
        for c in self.cases:
            new.add_case(c.clone())
        return new

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

    def update_module(self, module):
        for c in self.cases:
            c.update_module(module)

    def _reify(self):
        return {
            'opts': [o.reify() for o in self.opts],
            'cases': [c.reify() for c in self.cases]
        }

    def accept(self, visitor):
        for c in self.cases:
            c.accept(visitor)



class LiteralDispatchProxy(DispatchProxy):
    reification_type = u'_when'
    def __init__(self, path, opts):
        self.cases = []
        self.opts = opts
        self.path = path

    def clone(self):
        new = LiteralDispatchProxy(self.path, self.opts)
        for c in self.cases:
            new.add_case(c.clone())
        return new

    def instantiate(self, builder):
        d = Dispatch(self.path)
        for c in self.cases:
            d.add_case(c.instantiate(builder))
        return d

class TypeCaseProxy(Proxy):
    reification_type = u'_case'
    def __init__(self, path, via):
        self.cases = []
        self.path = path
        self.via = via

    def clone(self):
        new = TypeCaseProxy(self.path, self.via.clone() if self.via else None)
        for c in self.cases:
            new.add_case(c.clone())
        return new

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

    def update_module(self, module):
        if self.via:
            self.via.update_module(module)
        for c in self.cases:
            c.update_module(module)

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

    def accept(self, visitor):
        if self.via:
            self.via.accept(visitor)
        for c in self.cases:
            c.accept(visitor)

class TypeCondProxy(Proxy):
    reification_type = u'_cond'
    def __init__(self, path):
        self.cases = []
        self.path = path

    def clone(self):
        new =TypeCondProxy(self.path)
        for c in self.cases:
            new.add_case(c.clone())
        return new

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

    def update_module(self, module):
        for c in self.cases:
            c.update_module(module)

    def _reify(self):
        o = {
            'cases': [c.reify() for c in self.cases]
        }
        if self.path:
            p = self.path._to_str()
            o['path'] = unicode(p) if not isinstance(p, unicode) else p
        return o

    def accept(self, visitor):
        for c in self.cases:
            c.accept(visitor)

class BranchProxy(Proxy):
    def __init__(self, typedef, cmdproxy):
        self.typedef = typedef
        self.cmdproxy = cmdproxy
        self.type = None

    def clone(self):
        new = BranchProxy(self.typedef, self.cmdproxy.clone())
        return new

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

    def update_module(self, module):
        self.cmdproxy.update_module(module)

    def instantiate(self, builder):
        return Branch(self.type, self.cmdproxy.instantiate(builder))
        
    def reify(self):
        return {
            'type': self.typedef.reify() if self.typedef != u'*' else json.TagOnly(u'_wildcard'),
            'body': self.cmdproxy.reify()
        }
   
    def accept(self, visitor):
        self.cmdproxy.accept(visitor)

class ChoiceBranchItemProxy(Proxy):
    def __init__(self, typedef, cmdproxy):
        self.typedef = typedef
        self.cmdproxy = cmdproxy
        self.type = None

    def clone(self):
        new = ChoiceBranchItemProxy(self.typedef, self.cmdproxy.clone())
        return new

    def set_module(self, module):
        self.cmdproxy.set_module(module)

    def update_module(self, module):
        self.cmdproxy.update_module(module)
    
    def instantiate(self, builder):
        return Branch(self.type, self.cmdproxy.instantiate(builder))
        
    def reify(self):
        return {
            'type': self.typedef.reify() if self.typedef != u'*' else json.TagOnly(u'_wildcard'),
            'body': self.cmdproxy.reify()
        }

    def accept(self, visitor):
        self.cmdproxy.accept(visitor)

class TagProxy(Proxy):
    reification_type = u'_tag'
    def __init__(self, t, c):
        self.tag = t
        self.cmdproxy = c

    def clone(self):
        if isinstance(self.tag, unicode):
            return TagProxy(self.tag, self.cmdproxy.clone())
        else:
            return TagProxy(self.tag.clone(), self.cmdproxy.clone())

    def instantiate(self, builder):
        if isinstance(self.tag, unicode):
            return TagBuilder(self.tag, self.cmdproxy.instantiate(builder))
        else:
            return ExtendedTagBuilder(self.tag.instantiate(builder), self.cmdproxy.instantiate(builder))

    def set_module(self, module):
        if isinstance(self.tag, Proxy):
            self.tag.set_module(module)
        self.cmdproxy.set_module(module)

    def update_module(self, module):
        if not isinstance(self.tag, unicode):
            self.tag.update_module(module)
        self.cmdproxy.update_module(module)

    def _reify(self):
        return {
            'tag': self.tag,
            'value': self.cmdproxy.reify()
        }
    def accept(self, visitor):
        if not isinstance(self.tag, unicode):
            self.tag.accept(visitor)
        self.cmdproxy.accept(visitor)

class UnaryTagProxy(Proxy):
    reification_type = u'_unaryTag'
    def __init__(self, t):
        self.tag = t

    def clone(self):
        if isinstance(self.tag, unicode):
            return UnaryTagProxy(self.tag)
        else:
            return UnaryTagProxy(self.tag.clone())

    def instantiate(self, builder):
        if isinstance(self.tag, unicode):
            return UnaryTagBuilder(self.tag)
        else:
            return ExtendedUnaryTagBuilder(self.tag.instantiate(self))

    def set_module(self, module):
        if not isinstance(self.tag, unicode):
            self.tag.set_module(module)

    def update_module(self, module):
        if not isinstance(self.tag, unicode):
            self.tag.update_module(module)

    def _reify(self):
        return {
            'tag': self.tag
        }

    def accept(self, visitor):
        if not isinstance(self.tag, unicode):
            self.tag.accept(visitor)

class ParTagProxy(Proxy):
    reification_type = u'_tag'
    def __init__(self, t, c):
        self.tagcmd = t
        self.cmdproxy = c
    
    def clone(self):
        return ParTagProxy(self.tagcmd.clone(), self.cmdproxy.clone())

    def instantiate(self, builder):
        return ParTagBuilder(self.tagcmd.instantiate(builder), self.cmdproxy.instantiate(builder))

    def set_module(self, module):
        self.tagcmd.set_module(module)
        self.cmdproxy.set_module(module)

    def update_module(self, module):
        self.tagcmd.update_module(module)
        self.cmdproxy.update_module(module)

    def _reify(self):
        return {
            'tag': self.tag,
            'value': self.cmdproxy.reify()
        }

    def accept(self, visitor):
        self.tagcmd.accept(visitor)
        self.cmdproxy.accept(visitor)

class CaseProxy(TagProxy):
    def clone(self):
        return CaseProxy(self.tag, self.cmdproxy.clone())

    def instantiate(self, builder):
        return Case(self.tag, self.cmdproxy.instantiate(builder))

class UntagCaseProxy(TagProxy):
    reification_type = u'_untag'
    def clone(self):
        return UntagCaseProxy(self.tag, self.cmdproxy.clone())

    def instantiate(self, builder):
        return UntagCase(self.tag, self.cmdproxy.instantiate(builder))

class FunctorProxy(Proxy):
    def __init__(self, c, opts):
        self.cmdproxy = c
        self.opts = opts

    def clone(self):
        return self.__class__(self.cmdproxy.clone(), self.opts)

    def instantiate(self, builder):
        r = self._get_class()(self.cmdproxy.instantiate(builder), self.opts)
        builder.set_facility_to(r)
        return r

    def set_module(self, module):
        self.cmdproxy.set_module(module)

    def update_module(self, module):
        self.cmdproxy.update_module(module)
    
    def _reify(self):
        return {
            'opts': [o.reify() for o in self.opts],
            'body': self.cmdproxy.reify()
        }

    def accept(self, visitor):
        self.cmdproxy.accept(visitor)

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
    def clone(self):
        return RepeatProxy()

    def instantiate(self, builder):
        return Repeat()

    def set_module(self, module):
        pass

    def reify(self):
        return TagOnly(u'_repeat')

    def accept(self, visitor):
        pass

class CombinatorProxy(Proxy):
    def __init__(self, a, b):
        self.a = a
        self.b = b
        self.reification_type = u'_pipe' if not isinstance(self.b, DiscardProxy) else u'_discard'

    def clone(self):
        return CombinatorProxy(self.a.clone(), self.b.clone())

    def instantiate(self, builder):
        if isinstance(self.b, DiscardProxy):
            return DiscardCombinator(self.a.instantiate(builder), self.b.instantiate(builder))
        else:
            return CommandCombinator(self.a.instantiate(builder), self.b.instantiate(builder))

    def set_module(self, module):
        self.a.set_module(module)
        self.b.set_module(module)

    def update_module(self, module):
        self.a.update_module(module)
        self.b.update_module(module)

    def _reify(self):
        return [self.a.reify(), self.b.reify()]

    def accept(self, visitor):
        self.a.accept(visitor)
        self.b.accept(visitor)

class VarStoreProxy(CommandProxy):
    reification_type = u'_store'
    def __init__(self, name):
        self.name = name

    def clone(self):
        return VarStoreProxy(self.name)

    def instantiate(self, builder):
        return VarStore(self.name)

    def set_module(self, module):
        pass

    def update_module(self, module):
        pass

    def _reify(self):
        return {
            'name': self.name
        }

    def accept(self, visitor):
        pass

class VarRefProxy(CommandProxy):
    reification_type = u'_varref'
    def __init__(self, name, optional, default):
        self.name = name
        self.optional = optional
        self.default = default

    def clone(self):
        return VarRefProxy(self.name, self.optional, self.default)

    def instantiate(self, builder):
        return VarRef(self.name, self.optional, self.default)

    def set_module(self, module):
        pass

    def update_module(self, module):
        pass

    def _reify(self):
        return {
            'name': self.name,
            'optional': self.optional
        }

    def accept(self, visitor):
        pass

class ArgRefProxy(CommandProxy):
    reification_type = u'_argref'
    def __init__(self, name, optional, default=UNDEFINED):
        self.name = name
        self.optional = optional
        self.default = default

    def clone(self):
        return ArgRefProxy(self.name, self.optional, self.default)

    def instantiate(self, builder):
        return ArgRef(self.name, self.optional, self.default)

    def set_module(self, module):
        pass

    def update_module(self, module):
        pass

    def _reify(self):
        return {
            'name': self.name,
            'optional': self.optional
        }

    def accept(self, visitor):
        pass

class DiscardProxy(Proxy):
    def __init__(self, target):
        self.target = target

    def clone(self):
        return DiscardProxy(self.target.clone())

    def instantiate(self, builder):
        return self.target.instantiate(builder)
    
    def set_module(self, module):
        self.target.set_module(module)

    def update_module(self, module):
        self.target.update_module(module)

    def reify(self):
        return self.target.reify()

    def accept(self, visitor):
        self.target.accept(visitor)

class FragmentProxy(Proxy):
    reification_type = u'_fragment'
    def __init__(self, c, fragment_name):
        self.cmdproxy = c
        self.fragment_name = fragment_name

    def clone(self):
        return FragmentProxy(self.cmdproxy.clone(), self.fragment_name)

    def instantiate(self, builder):
        r = PipelineFragment(self.cmdproxy.instantiate(builder), self.fragment_name)
        builder.set_facility_to(r)
        return r

    def set_module(self, module):
        self.cmdproxy.set_module(module)

    def update_module(self, module):
        self.cmdproxy.update_module(module)

    def _reify(self):
        return {
            'name': self.fragment_name,
            'body': self.cmdproxy.reify()
        }   

    def accept(self, visitor):
        self.cmdproxy.accept(visitor)

class EnvelopeProxy(Proxy):
    def __init__(self, c, name):
        self.cmdproxy = c
        self.action_name = name

    def clone(self):
        return EnvelopeProxy(self.cmdproxy.clone(), self.action_name)

    def instantiate(self, builder):
        r = ActionEnvelope(self.cmdproxy.instantiate(builder), self.action_name)
        return r

    def set_module(self, module):
        self.cmdproxy.set_module(module)

    def update_module(self, module):
        self.cmdproxy.update_module(module)

    def reify(self):
        return None #throw_caty_exception('RuntimeError', u'Action command can not reified by inspect:reify-cmd')

    def accept(self, visitor):
        self.cmdproxy.accept(visitor)

class JsonPathProxy(Proxy):
    reification_type = u'_jsonPath'
    def __init__(self, stm, pos):
        self.stm = stm
        self.pos = pos

    def clone(self):
        return JsonPathProxy(self.stm, self.pos)

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

    def accept(self, visitor):
        pass

class TryProxy(Proxy):
    def __init__(self, pipeline, opts):
        self.pipeline = pipeline
        self.opts = opts

    def clone(self):
        return TryProxy(self.pipeline.clone(), self.opts)

    def instantiate(self, builder):
        return Try(self.pipeline.instantiate(builder), self.opts)

    def set_module(self, module):
        self.pipeline.set_module(module)

    def update_module(self, module):
        self.pipeline.update_module(module)

    def accept(self, visitor):
        self.pipeline.accept(visitor)

class CatchProxy(Proxy):
    def __init__(self, handler):
        self.handler = handler

    def clone(self):
        return CatchProxy(dict([(k, v.clone()) for k, v in self.handler.items()]) if self.handler is not None else None)

    def instantiate(self, builder):
        return Catch(dict([(k, v.instantiate(builder)) for k, v in self.handler.items()]) if self.handler is not None else None)

    def set_module(self, module):
        if self.handler:
            for v in self.handler.values():
                v.set_module(module)

    def update_module(self, module):
        if self.handler:
            for v in self.handler.values():
                v.update_module(module)

    def accept(self, visitor):
        if self.handler:
            for v in self.handler.values():
                v.accept(visitor)

class UncloseProxy(Proxy):
    def __init__(self, pipeline, opts):
        self.pipeline = pipeline
        self.opts = opts

    def clone(self):
        return UncloseProxy(self.pipeline.clone(), self.opts)

    def instantiate(self, builder):
        return Unclose(self.pipeline.instantiate(builder), self.opts)

    def set_module(self, module):
        self.pipeline.set_module(module)

    def update_module(self, module):
        self.pipeline.update_module(module)

    def accept(self, visitor):
        self.pipeline.accept(visitor)

class ChoiceBranchProxy(Proxy):
    reification_type = u'_branch'
    def __init__(self):
        self.cases = []

    def clone(self):
        new = ChoiceBranchProxy()
        for c in self.cases:
            new.add_case(c.clone())
        return new

    def add_case(self, node):
        self.cases.append(node)

    def instantiate(self, builder):
        o = ChoiceBranch()
        for n in self.cases:
            o.add_case(n.instantiate(builder))
        return o

    def set_module(self, module):
        for n in self.cases:
            n.set_module(module)

    def update_module(self, module):
        for n in self.cases:
            n.update_module(module)

    def _reify(self):
        o = {}
        for n in self.nodes:
            o[n.name] = n.reify()
        return o

    def accept(self, visitor):
        for n in self.cases:
            n.accept(visitor)

class EmptyProxy(Proxy):
    reification_type = u'_empty'
    def __init__(self):
        pass

    def clone(self):
        return self

    def instantiate(self, builder):
        return Empty()

    def set_module(self, module):
        pass

    def accept(self, visitor):
        pass

class BreakProxy(Proxy):
    reification_type = u'_empty'
    def __init__(self):
        pass

    def clone(self):
        return self

    def instantiate(self, builder):
        return Break()

    def set_module(self, module):
        pass

    def accept(self, visitor):
        pass

class MethodChainProxy(Proxy):
    def __init__(self, pipeline):
        self.pipeline = pipeline

    def clone(self):
        return MethodChainProxy(self.pipeline.clone())

    def instantiate(self, builder):
        return MethodChain(self.pipeline, builder)

    def set_module(self, module):
        self.pipeline.set_module(module)

    def update_module(self, module):
        self.pipeline.update_module(module)

    def accept(self, visitor):
        self.pipeline.accept(visitor)

class FetchProxy(Proxy):
    def __init__(self, queries, opts):
        self.queries = queries
        self.opts = opts

    def clone(self):
        return self

    def instantiate(self, builder):
        return Fetch(self.queries, self.opts)

    def set_module(self, module):
        pass

    def accept(self, visitor):
        pass

class MutatingProxy(Proxy):
    def __init__(self, pipeline, envname):
        self.pipeline = pipeline
        self.envname = envname

    def clone(self):
        return MutatingProxy(self.pipeline.clone(), self.envname)

    def instantiate(self, builder):
        return Mutating(self.pipeline.instantiate(builder), self.envname)

    def set_module(self, module):
        self.pipeline.set_module(module)

    def update_module(self, module):
        self.pipeline.update_module(module)

    def accept(self, visitor):
        self.pipeline.accept(visitor)

class CommitMProxy(Proxy):
    def __init__(self, args):
        self.args = args

    def clone(self):
        return self

    def instantiate(self, builder):
        return CommitM(self.args)

    def accept(self, visitor):
        pass

def combine_proxy(args):
    return reduce(CombinatorProxy, args)


class FoldProxy(FunctorProxy):
    reification_type = u'_fold'
    def _get_class(self):
        return Fold

class ClassProxy(Proxy):
    def __init__(self, name, type_args, command):
        self.name = name
        self.type_args = type_args
        self.command = command

    def clone(self):
        return ClassProxy(self.name, self.type_args, self.command.clone())

    def set_module(self, module):
        self.module = module

    def instantiate(self, builder):
        m = builder.get_class_module(self)
        self.command.set_module(m)
        return self.command.instantiate(builder)

    def accept(self, visitor):
        self.command.accept(visitor)

