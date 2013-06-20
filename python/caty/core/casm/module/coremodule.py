#coding: utf-8
from caty.core.casm.module.basemodule import *

class CoreModule(Module):
    u"""Caty付属のモジュール。
    コマンドクラスはすべてライブラリのサーチパス上にあり、
    スキーマはそれらの.pyファイルのdocstringなどから取得される。
    """
    def __init__(self, app, parent, is_root=False):
        Module.__init__(self, app)
        self.schema_ns = {}
        self.schema_ns.update(schemata)
        self.command_loader = BuiltinLoader()
        self.parent = parent
        self.is_root= is_root
        self.is_builtin = True
        self.filepath = u''
        self.compiled = False

    def compile(self, schema_string, name):
        if self.is_root:
            if name is None:
                self._name = u'builtin'
                for t in parse(schema_string):
                    t.declare(self)
            else:
                mod = self.__class__(self._app, self)
                mod.compile(schema_string, name)
                self.sub_modules[mod.name] = mod
        else:
            self._name = name
            for t in parse(schema_string):
                t.declare(self)

    def clear_namespace(self):
        Module.clear_namespace(self)
        self.schema_ns.update(schemata)

