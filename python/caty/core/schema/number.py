#coding: utf-8
from caty.core.schema.base import *
from decimal import Decimal
import caty.core.runtimeobject as ro
import random

class NumberSchema(ScalarSchema):
    minimum = attribute('minimum')
    maximum = attribute('maximum')
    is_integer = False
    __options__ = SchemaBase.__options__ | set(['minimum', 'maximum', 'is_integer'])

    def __init__(self, *args, **kwds):
        ScalarSchema.__init__(self, *args, **kwds)
        if self.minimum > self.maximum and self.maximum is not None:
            raise JsonSchemaError(dict(msg='minmum($min) is bigger than maximum($max)', min=self.minimum, max=self.maximum))

    def _validate(self, value):
        if not self.optional and value == None:
            raise JsonSchemaError(dict(msg=u'null is not allowed'))
        elif self.optional and value == None:
            return
        if self.is_integer:
            if not (isinstance(value, int) or (isinstance(value, Decimal) and value == int(value)))or isinstance(value, bool):
                raise JsonSchemaError(dict(msg=u'value should be $type', type='integer'), value, '')
        if isinstance(value, bool):
            raise JsonSchemaError(dict(msg=u'value should be $type', type='number'), value, '')
        if not isinstance(value, (Decimal, int)):
            raise JsonSchemaError(dict(msg=u'value should be $type', type='number'), value, '')
        if self.minimum != None and self.minimum > value:
            raise JsonSchemaError(dict(msg=u'value should be greater than $val', val=self.minimum), value, '')
        if self.maximum != None and self.maximum < value:
            raise JsonSchemaError(dict(msg=u'value should be smaller than $val', val=self.maximum), value, '')

    def intersect(self, another):
        minimum = max(self.minimum, another.minimum)
        if None in (self.maximum, another.maximum):
            maximum = self.maximum if another.maximum is None else another.maximum
        else:
            maximum = min(self.maximum, another.maximum)
        if minimum > maximum and maximum is not None:
            return NeverSchema()
        is_integer = self.is_integer or another.is_integer
        opts = {
            'minimum': minimum,
            'maximum': maximum,
            'is_integer': is_integer
        }
        return self.clone(opts)

    def _convert(self, value):
        try:
            if self.is_integer:
                return int(value)
            return Decimal(value)
        except:
            raise JsonSchemaError(dict(msg=u'An error occuered while converting to $type', type=self.type), value, '')

    def _rand_int(self):
        import sys
        min_i = self.minimum or 0
        max_i = self.maximum or 100
        return random.randint(min_i, max_i)

    def _rand_number(self):
        min_i = self.minimum or 0
        max_i = self.maximum or 100.0
        return random.uniform(min_i, max_i)

    def dump(self, depth, node=[]):
        if self.is_integer:
            return 'integer'
        return 'number'

    @property
    def type(self):
        if self.is_integer:
            return 'integer'
        return 'number'

class IntegerSchema(NumberSchema):
    is_integer = True

