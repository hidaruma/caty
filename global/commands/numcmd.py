# -*- coding: utf-8 -*- 
# 
#
from caty.command import Command
import caty.jsontools as xjson
from caty.core.exception import throw_caty_exception
from decimal import Decimal

class FromString(Command):
    def execute(self, input):
        try:
            return Decimal(input)
        except:
            throw_caty_exception(u'InvalidInput', u'bad number format')

class Add(Command):
    def execute(self, input):
        r = 0
        for x in input:
            r += x
        return r

class Mul(Command):
    def execute(self, input):
        r = 1
        for x in input:
            r *= x
        return r

class Sub(Command):
    def execute(self, input):
        return input[0] - input[1]

class Div(Command):
    def setup(self, opts):
        self.integer = opts.get('integer')

    def execute(self, input):
        r = Decimal(input[0]) / input[1]
        return Decimal(long(r)) if self.integer else r

class Mod(Command):
    def execute(self, input):
        return input[0] % input[1]



class Gt(Command):
    def setup(self, opts):
        self.boolean = opts.get('boolean')

    def execute(self, input):
        if input[0] > input[1]:
            return True if self.boolean else xjson.tagged(u'True', input)
        else:
            return False if self.boolean else xjson.tagged(u'False', input)

class Ge(Command):
    def setup(self, opts):
        self.boolean = opts.get('boolean')

    def execute(self, input):
        if input[0] >= input[1]:
            return True if self.boolean else xjson.tagged(u'True', input)
        else:
            return False if self.boolean else xjson.tagged(u'False', input)

# 以下、まだやってない

class Le(Command):
    def setup(self, opts):
        self.boolean = opts.get('boolean')

    def execute(self, input):
        pass

class Lt(Command):
    def setup(self, opts):
        self.boolean = opts.get('boolean')

    def execute(self, input):
        pass

