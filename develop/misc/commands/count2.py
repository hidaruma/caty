# -*- coding: utf-8 -*- 
#
#  count2
#
from caty.command import Command
from caty.jsontools import tagged
from count2fcl import *

       
class Initialize(Command):
    def setup(self, config=None):
        self.config = config

    def execute(self, app_instance):
        return Counter.initialize(app_instance, 
                                  self.config)


class Finalize(Command):
    def execute(self, app_instance):
        return Counter.finalize(app_instance)


class Create(Command):
    def setup(self, system_param, mode, user_param=None):
        self.system_param = system_param
        self.mode = mode
        self.user_param = user_param

    def execute(self, app_instance):
        return Counter.create(app_instance, 
                              self.system_param, self.mode, self.user_param)

class List(Command):
    def execute(self):
        return Counter.list()



class Value(Command):
    def setup(self, arg1):
        self.arg1 = arg1

    def execute(self):
        counter = self.arg1
        return counter.value()

class Inc(Command):
    def setup(self, arg1):
        self.arg1 = arg1

    def execute(self):
        counter = self.arg1
        counter.inc()
        return counter

class Dec(Command):
    def setup(self, arg1):
        self.arg1 = arg1

    def execute(self):
        counter = self.arg1
        counter.dec()
        return counter

class Reset(Command):
    def setup(self, arg1):
        self.arg1 = arg1

    def execute(self):
        counter = self.arg1
        counter.reset()
        return counter

class Start(Command):
    def setup(self, arg1):
        self.arg1 = arg1

    def execute(self):
        counter = self.arg1
        return counter.start()


class Commit(Command):
    def setup(self, arg1):
        self.arg1 = arg1

    def execute(self):
        counter = self.arg1
        counter.commit()
        return counter

class Cancel(Command):
    def setup(self, arg1):
        self.arg1 = arg1

    def execute(self):
        counter = self.arg1
        counter.cancel()
        return counter

class Cleanup(Command):
    def setup(self, arg1):
        self.arg1 = arg1

    def execute(self):
        counter = self.arg1
        counter.cleanup()
        return counter
