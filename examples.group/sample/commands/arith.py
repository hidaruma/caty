# -*- coding: utf-8 -*- 
# arith.py
#
from caty.command import Command

class Inc(Command):
    def execute(self, input):
        return input + 1

class Sq(Command):
    def execute(self, input):
        return input * input
