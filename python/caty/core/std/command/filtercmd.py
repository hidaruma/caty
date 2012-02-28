#coding: utf-8
name = u'filter'
schema = u''
from caty.core.command import Builtin
import caty

class NotNullFilter(Builtin):

    def execute(self, a):
        return a != None and a != caty.UNDEFINED

class NotEmptyFilter(Builtin):

    def execute(self, a):
        return a != [] and a != {} and a != '' and a != None and a != caty.UNDEFINED

class EmptyFilter(Builtin):

    def execute(self, a):
        return a == [] or a == {} or a == '' or a == None or a == caty.UNDEFINED

class ModuloFilter(Builtin):

    def setup(self, mod):
        self.mod = mod

    def execute(self, a):
        return a % a.__class__(self.mod)

class EqFilter(Builtin):

    def setup(self, arg):
        self.arg = arg

    def execute(self, a):
        return a == self.arg

class NotEqFilter(Builtin):

    def setup(self, arg):
        self.arg = arg

    def execute(self, a):
        return a != self.arg

class NotFilter(Builtin):

    def execute(self, b):
        return not b

import caty
class DefinedFilter(Builtin):

    def execute(self, i):
        return i is not caty.UNDEFINED

class RawStringFilter(Builtin):

    def execute(self, s):
        from caty.template.core.context import VariableString, RawString
        if isinstance(s, VariableString):
            return RawString(s.string)
        else:
            return RawString(s if isinstance(s, basestring) else str(s))

class IsObject(Builtin):

    def execute(self, input):
        if isinstance(input, dict):
            return True
        else:
            return False

class IsArray(Builtin):

    def execute(self, input):
        if isinstance(input, list):
            return True
        else:
            return False

