# coding: utf-8
from caty.core.command import Builtin

class Diff(Builtin):
    def execute(self, input):
        return list(set(input[0]).difference(set(input[1])))
