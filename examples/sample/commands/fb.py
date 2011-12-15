# -*- coding: utf-8 -*- 
# 
#
from caty.command import Command
from caty.jsontools import tagged

class Inc(Command):
    def execute(self, input):
        return input + 1

class Dividable(Command):
    def setup(self, n):
        self.n = n
    def execute(self, input):
        r = input % self.n
        if r == 0:
            return tagged('True', input)
        else:
            return tagged('False', input)

# coutの代替
class Say(Command):
    def execute(self, input):
        t = type(input)
        if (t is int) or (t is float):
            print "%d" % input
        else: # t is unicode
            print "%s" % input
        return None
