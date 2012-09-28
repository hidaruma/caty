# -*- coding: utf-8 -*- 
# 
#
from caty.command import Command
import caty.jsontools as xjson
from caty.core.exception import throw_caty_exception
from decimal import Decimal
from caty.jsontools import normalize_number

def normalize_number_wrapper(f):
    def _wrapped(*args, **kwds):
        return normalize_number(f(*args, **kwds))
    return _wrapped

class FromString(Command):
    def execute(self, input):
        try:
            return Decimal(input)
        except:
            throw_caty_exception(u'InvalidInput', u'bad number format')

class Add(Command):
    @normalize_number_wrapper
    def execute(self, input):
        r = 0
        for x in input:
            r += x
        return r

class Mul(Command):
    @normalize_number_wrapper
    def execute(self, input):
        r = 1
        for x in input:
            r *= x
        return r

class Sub(Command):
    @normalize_number_wrapper
    def execute(self, input):
        return input[0] - input[1]

class Div(Command):
    @normalize_number_wrapper
    def setup(self, opts):
        self.integer = opts.get('integer')

    def execute(self, input):
        r = Decimal(str(float(input[0]))) / input[1]
        return long(r) if self.integer else r

class Mod(Command):
    @normalize_number_wrapper
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

class Le(Command):
    def setup(self, opts):
        self.boolean = opts.get('boolean')

    def execute(self, input):
        if input[0] <= input[1]:
            return True if self.boolean else xjson.tagged(u'True', input)
        else:
            return False if self.boolean else xjson.tagged(u'False', input)

class Lt(Command):
    def setup(self, opts):
        self.boolean = opts.get('boolean')

    def execute(self, input):
        if input[0] < input[1]:
            return True if self.boolean else xjson.tagged(u'True', input)
        else:
            return False if self.boolean else xjson.tagged(u'False', input)

