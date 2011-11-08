# coding:utf-8
from caty.core.command import Builtin, Command, scriptwrapper
class CommandBuilder(object):
    def __init__(self, facilities, namespace):
        self.facilities = facilities
        self.namespace = namespace

    def build(self, proxy, type_args, opts_ref, args_ref):
        u"""コマンド文字のチャンクをコマンド名と引数のリストに分割し、呼び出し可能なコマンドオブジェクトを返す。
        """
        from caty.core.script.proxy import Proxy
        if proxy.module:
            try:
                profile = proxy.module.get_command_type(proxy.name)
            except:
                print proxy.module.name, proxy.module.parent
                raise
        else:
            profile = self.namespace[proxy.name]
        cls = profile.get_command_class()
        if isinstance(cls, Proxy):
            cmd = scriptwrapper(profile, cls.instantiate(self))(opts_ref, args_ref, type_args)
        else:
            cmd = cls(opts_ref, args_ref, type_args)
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

    def accept(self, visitor):
        return visitor.visit_pipe(self)

    def __call__(self, input):
        r = self.bf(input)
        return self.af(r)

    def __repr__(self):
        return '%s | %s' % (repr(self.bf), repr(self.af))

class DiscardCombinator(CommandCombinator):
    def __call__(self, input):
        self.bf(input)
        return self.af(None)

    def accept(self, visitor):
        return visitor.visit_discard_pipe(self)

def combine(chunks):
    return reduce(CommandCombinator, chunks)

