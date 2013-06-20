#coding: utf-8
from caty.core.casm.module.basemodule import *
from caty.core.casm.module.appmodule import *
from caty.core.casm.module.coremodule import *

class IntegratedModule(object):
    u"""標準モジュールとユーザ定義モジュールの複合モジュール
    """
    def __init__(self, system):
        coreapp = system._core_app
        self._core = CoreModule(coreapp, None, True)
        self._system = system
        self._global = None

    def compile(self, *args):
        self._core.compile(*args)

    def resolve(self):
        self._core.resolve()
    
    def make_blank_module(self, app):
        app_module = AppModule(app, app.parent._schema_module, True)
        return app_module

    def make_app_module(self, app):
        app_module = AppModule(app, app.parent._schema_module, True)
        app_module.compile()
        return app_module


