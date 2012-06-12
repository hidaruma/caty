# -*- coding: utf-8 -*- 
#
#  count3cmd
#
from caty.command import Command
from caty.jsontools import tagged
from count3fcl import *

       
class Initialize(Command):
    def setup(self, config=None):
        self.config = config

    def execute(self, app_instance):
        return Counter.initialize(app_instance, 
                                  self.config)


class Finalize(Command):
    def execute(self, app_instance):
        return Counter.finalize(app_instance)


class Instance(Command):
    def setup(self, system_param=None):
        self.system_param = system_param

    def execute(self, app_instance):
        return Counter.instance(app_instance, self.system_param)

class Create(Command):
    def setup(self, mode=u'use', user_param=None):
        self.mode = mode
        self.user_param = user_param

    def execute(self):
        return self.arg0.create(self.mode, self.user_param)

class ListNames(Command):
    def execute(self):
        return Counter.list_names()

class IsReady(Command):
    def execute(self):
        return Counter.is_ready()

class Dump(Command):
    def execute(self):
        return Counter.dump()

class Who(Command):
    def execute(self):
        counter= self.arg0
        return counter.who()


class Start(Command):
    def execute(self):
        counter_req = self.arg0
        return counter_req.start()

class Commit(Command):
    def execute(self):
        counter_req = self.arg0
        counter_req.commit()

class Cancel(Command):
    def execute(self):
        counter_req = self.arg0
        counter_req.cancel()

class Cleanup(Command):
    def execute(self):
        counter_req = self.arg0
        counter_req.cleanup()

# 固有コマンド

class Value(Command):
    def execute(self):
        counter_req = self.arg0
        return counter_req.value()

class Inc(Command):
    def execute(self):
        counter_req = self.arg0
        counter_req.inc()

class Dec(Command):
    def execute(self):
        counter_req = self.arg0
        counter_req.dec()

class Reset(Command):
    def execute(self):
        counter_req = self.arg0
        counter_req.reset()
