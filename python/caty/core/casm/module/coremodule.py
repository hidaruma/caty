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

    def _load_facility_class(self, name, uri):
        if not uri.startswith(u'python:'):
            raise Exception(self.application.i18n.get(u'Invalid reference: $ref, $name, $mod', ref=uri, name=name, mod=self.name))
        uri = uri.replace('python:', '')
        lib, cls = uri.split('.', 1)
        code = 'from caty.core.std.lib.%s import %s' % (lib, cls)
        g_dict = {}
        obj = compile(code, 'python/caty/core/std/lib/' + lib +'.py', 'exec')
        g_dict['__file__'] = 'python/caty/core/std/lib/' + lib +'.py'
        exec obj in g_dict
        return g_dict[cls]
