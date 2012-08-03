# coding:utf-8
from caty.core.command import Builtin, Command, scriptwrapper
class CommandBuilder(object):
    def __init__(self, facilities, namespace):
        self.facilities = facilities
        self.namespace = namespace
        self.trace = {}

    def build(self, proxy, type_args, opts_ref, args_ref, pos, module):
        u"""コマンド文字のチャンクをコマンド名と引数のリストに分割し、呼び出し可能なコマンドオブジェクトを返す。
        """
        from caty.core.script.proxy import Proxy
        if proxy.module:
            try:
                profile = proxy.module.schema_finder.get_command(proxy.name)
            except:
                raise
        else:
            profile = self.namespace.get_command(proxy.name)
        cls = profile.get_command_class()
        if isinstance(cls, Proxy):
            if cls in self.trace:
                obj = self.trace[cls]
            else:
                obj = scriptwrapper(profile, lambda :cls.instantiate(self))
                self.trace[cls] = obj
            cmd = obj(opts_ref, args_ref, type_args, pos, module)
        else:
            cmd = cls(opts_ref, args_ref, type_args, pos, module)
        return cmd

    def set_facility_to(self, c):
        u"""Syntax オブジェクトなど、通常の処理経路をたどらないオブジェクトにファシリティを追加する。
        """
        c.set_facility(self.facilities)


class CommandCombinator(Command):
    u"""二つのコマンドを受け取り、それらを順次実行するコマンドのラッパークラス。
    """
    def __init__(self, bf, af):
        self.bf = bf
        self.af = af

    def convert(self, value):
        return self.bf.convert(value)

    def set_facility(self, facilities):
        self.bf.set_facility(facilities)
        self.af.set_facility(facilities)

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

