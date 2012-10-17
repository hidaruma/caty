#coding: utf-8
from caty.core.command import Builtin, Internal
from caty.core.exception import *

class SysInstance(Builtin):
    def execute(self):
        return self.current_app._system

class AppInstance(Builtin):
    def setup(self, name=None):
        self.__app_name = name

    def execute(self):
        if not self.__app_name:
            return self.current_app
        return self.current_app._system.get_app(self.__app_name)




