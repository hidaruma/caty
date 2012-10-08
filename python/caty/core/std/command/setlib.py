# coding: utf-8
from caty.core.command import Builtin
import caty.jsontools as json

class Diff(Builtin):
    def execute(self, input):
        return list(set(input[0]).difference(set(input[1])))


class Union(Builtin):
    def execute(self, input):
        ss = input
        r = set([])
        while len(ss) != 0:
            r = (r | set(ss[0]))
            ss = ss[1:]
        return list(r)

class Meet(Builtin):
    def execute(self, input):
        ss = input
        r = set([])
        while len(ss) != 0:
            r = (r & set(ss[0]))
            ss = ss[1:]
        return list(r)

class Empty(Builtin):
    def execute(self):
        return []

class IsEmpty(Builtin):
    def execute(self, input):
        if len(input) == 0:
            return json.tagged('True', input)
        else:
            return json.tagged('False', input)

class AreDisjoint(Builtin):
    def execute(self, input):
        s1 = set(input[0])
        s2 = set(input[1])
        if len(s1 & s2) == 0:
            return json.tagged('True', input)
        else:
            return json.tagged('False', input)

class Normalize(Builtin):
    def execute(self, input):
        return list(set(input))

