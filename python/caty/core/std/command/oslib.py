#coding: utf-8
from __future__ import with_statement
from caty.core.command import Builtin
from caty.core.exception import *
import caty.jsontools as json
from subprocess import Popen, list2cmdline
import sys
import os

class ExecScript(Builtin):
    def setup(self, path, *args):
        self.__path = path
        self.__args = list(args) if args else []

    def execute(self):
        script = self.scripts.open('/' + self.__path)
        if not script.exists:
            throw_caty_exception(u'ScriptNotFound', u'Script does not exists: $path', path=self.__path)
        cwd = os.path.join(self.env.get('CATY_HOME'), self.current_app._group.name, self.current_app.name)
        if sys.platform == 'win32':
            p = Popen(list2cmdline([script.real_path] + self.__args), cwd=cwd)
        else:
            p = Popen([script.real_path] + self.__args, cwd=cwd)
        try:

            ret = p.wait()
            return ret
        except:
            throw_caty_exception(u'CommandExecutionError', u'An error occuered while running script: $path', path=self.__path)

class Status(Builtin):
    def execute(self, input):
        if input == 0:
            return json.tagged(u'OK', 0)
        else:
            return json.tagged(u'NG', input)

        




