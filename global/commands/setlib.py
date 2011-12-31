# -*- coding: utf-8 -*- 
# 
#
from caty.command import Command
import caty.jsontools as json

class Diff(Command):
    def execute(self, input):
        s1 = set(input[0])
        s2 = set(input[1])
        return list(s1 - s2)

class Union(Command):
    def execute(self, input):
        s1 = set(input[0])
        s2 = set(input[1])
        return list(s1 | s2)

class Meet(Command):
    def execute(self, input):
        s1 = set(input[0])
        s2 = set(input[1])
        return list(s1 & s2)

class Empty(Command):
    def execute(self):
        return []

class IsEmpty(Command):
    def execute(self, input):
        if len(input) == 0:
            return json.tagged('True', input)
        else:
            return json.tagged('False', input)

class AreDisjoint(Command):
    def execute(self, input):
        s1 = set(input[0])
        s2 = set(input[1])
        if len(s1 & s2) == 0:
            return json.tagged('True', input)
        else:
            return json.tagged('False', input)

class Normalize(Command):
    def execute(self, input):
        return list(set(input))

