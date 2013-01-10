# -*- coding: utf-8 -*- 
# 
from caty.command import Command

class Val(Command):
    def execute(self):
        return self.countA.value()

class Up(Command):
    def execute(self):
        self.countA.inc()
        return None
