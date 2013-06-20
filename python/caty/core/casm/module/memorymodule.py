#coding: utf-8
from caty.core.casm.module.basemodule import *

class InMemoryModule(Module):
    u"""schemataからの読み出しではなく、文字列を直に渡されて構築される。
    """
    def __init__(self, app, parent):
        Module.__init__(self, app)
        self.schema_ns = {}
        self.command_loader = CommandLoader(app._command_fs)
        self.parent = parent
        self.is_root= False
        self.is_builtin = False
        self.filepath = u''
        self.compiled = False

    def compile(self, schema_string):
        from caty.core.casm.language.ast import ModuleName
        for t in parse(schema_string):
            if isinstance(t, ModuleName):
                self._name = t.name
            t.declare(self)
