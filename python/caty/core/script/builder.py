# coding:utf-8
from caty.core.command import Builtin, Command, scriptwrapper
from caty.core.exception import CatyException, SystemResourceNotFound
from caty.core.schema import TypeVariable

class CommandBuilder(object):
    def __init__(self, facilities, namespace):
        self.facilities = facilities
        self.namespace = namespace
        self.trace = {}

    def build(self, proxy, type_args, opts_ref, args_ref, pos, module):
        u"""コマンド文字のチャンクをコマンド名と引数のリストに分割し、呼び出し可能なコマンドオブジェクトを返す。
        """
        try:
            if proxy.module:
                profile = proxy.module.schema_finder.get_command(proxy.name)
            else:
                profile = self.namespace.get_command(proxy.name)
            return self.make_cmd(profile, type_args, opts_ref, args_ref, pos, module)
        except CatyException as e:
            if isinstance(e, SystemResourceNotFound):
                return NullCommand(e)
            raise

    def make_cmd(self, profile, type_args, opts_ref, args_ref, pos, module):
        from caty.core.script.proxy import Proxy, EnvelopeProxy
        from caty.core.script.proxy import VarRefProxy as VarRef
        from caty.core.command.param import Option, OptionVarLoader, Argument, NamedArg
        cls = profile.get_command_class()
        if isinstance(cls, Proxy):
            cls.update_module(module)
            obj = scriptwrapper(profile, lambda :cls.instantiate(self))
            cmd = obj(opts_ref, args_ref, type_args, pos, module)
        else:
            cmd = cls(opts_ref, args_ref, type_args, pos, module)
        return cmd

    def set_facility_to(self, c):
        u"""Syntax オブジェクトなど、通常の処理経路をたどらないオブジェクトにファシリティを追加する。
        """
        c.set_facility(self.facilities)

    def get_class_module(self, cls_proxy):
        cls = ClassModuleWrapper(cls_proxy.module.get_class(cls_proxy.name), cls_proxy.type_args)
        return cls

class ClassModuleWrapper(object):
    def __init__(self, module, type_args):
        self.module = module
        self.schema_finder = module.schema_finder
        self.type_params = []
        rr = module.make_reference_resolver()
        for p in module.type_params:
            schema = TypeVariable(p.var_name, [], p.kind, p.default, {}, module)
            self.type_params.append(schema.accept(rr))
        schema = module.schema_finder
        l = len(type_args)
        _ta = []
        for i, p in enumerate(self.type_params):
            if i < l:
                s = type_args[i]
                sb = module.make_schema_builder()
                sb._type_params = self.type_params
                rr = module.make_reference_resolver()
                tn = module.make_type_normalizer()
                ta = module.make_typevar_applier()
                ta._init_type_params(self)
                ta.real_root = False
                t = tn.visit(s.accept(sb).accept(rr)).accept(ta)
                x = p.clone(set())
                x._schema = t
                _ta.append(x)
        if _ta:
            self._apply_type_params(_ta, type_args)

    def _apply_type_params(self, type_params, type_args):
        if not type_params:
            return
        tp = []
        for param, _, arg in zip(type_params, type_args, self.type_params):
            param.var_name = arg.var_name
            tp.append(param)
        if tp:
            self.type_params = tp

    def apply(self, type):
        tc = self.module.make_typevar_applier()
        tc._init_type_params(self)
        tc.real_root = False
        r = type.accept(tc)
        return r 

    def __getattr__(self, name):
        return getattr(self.module, name)

class NullCommand(Command):
    def __init__(self, e):
        self.orig = e

    def set_facility(self, *args):
        pass

    def set_var_storage(self, *args):
        Command.set_var_storage(self, *args)

    def accept(self, visitor):
        raise self.orig


class CommandCombinator(Command):
    u"""二つのコマンドを受け取り、それらを順次実行するコマンドのラッパークラス。
    """
    def __init__(self, bf, af):
        self.bf = bf
        self.af = af

    def convert(self, value):
        return self.bf.convert(value)

    def set_facility(self, facilities, app=None):
        self.bf.set_facility(facilities, app)
        self.af.set_facility(facilities, app)

    def set_var_storage(self, storage):
        self.bf.set_var_storage(storage)
        self.af.set_var_storage(storage)

    @property
    def in_schema(self):
        return self.bf.in_schema

    @property
    def out_schema(self):
        return self.af.out_schema

    @property
    def var_storage(self):
        return self.af.var_storage

    @property
    def profile_container(self):
        return self.bf.profile_container

    @property
    def col(self):
        return self.bf.col

    @property
    def line(self):
        return self.bf.line

    def accept(self, visitor):
        return visitor.visit_pipe(self)

    def __call__(self, input):
        r = self.bf(input)
        return self.af(r)

    def __repr__(self):
        return '%s | %s' % (repr(self.bf), repr(self.af))

    def _prepare(self):
        self._prepare_opts()
        self._set_profile()
        self._finish_opts()

    def _prepare_opts(self):
        self.bf._prepare_opts()
        self.af._prepare_opts()

    def _set_profile(self):
        self.bf._set_profile()
        self.af._set_profile()

    def _finish_opts(self):
        self.bf._finish_opts()
        self.af._finish_opts()

    def apply_type_params(self, type_params):
        self.bf.apply_type_params(type_params)
        self.af.apply_type_params(type_params)

class DiscardCombinator(CommandCombinator):
    def __call__(self, input):
        self.bf(input)
        return self.af(None)

    def accept(self, visitor):
        return visitor.visit_discard_pipe(self)

def combine(chunks):
    return reduce(CommandCombinator, chunks)

