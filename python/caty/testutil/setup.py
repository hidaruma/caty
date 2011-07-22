#!/usr/bin/env python
#coding:utf-8
import cmd, glob, os
from caty.shell.system import setup_caty, StdStream, StreamWrapper
from caty.core.script.builder import CommandCombinator
from caty.core.script.parser import NothingTodo
from caty.jsontools import pp
from caty.mafs.authorization import AuthoriToken
from caty.session.value import create_env_skelton, create_variable
import caty
class TestEnv(object):
    def __init__(self, site):
        facilities = site.create_facilities(None)
        site.init_env(facilities, True, [u'test', u'console'], {})
        self.site = site
        self.registrar = site.registrar
        self.shell_interpreter = site.interpreter.shell_mode(facilities)
        self.file_interpreter = site.interpreter.shell_mode(facilities)
        self.interpreter = self.file_interpreter
        facilities['interpreter'] = self.interpreter
        self.facilities = facilities

    def build_command(cls, opts, args):
        c = cls(opts, args)
        c.set_facility(self.facilities)
        c._prepare()
        return c

def setup_testsite():
    s = setup_caty()
    return TestEnv(s)

