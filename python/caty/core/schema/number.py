#coding: utf-8
from caty.core.schema.base import *
from decimal import Decimal
import caty.core.runtimeobject as ro
import random
from caty.core.exception import throw_caty_exception, CatyException
from caty.core.typeinterface import AttrRef

class NumberSchema(ScalarSchema):
    minimum = attribute('minimum')
    maximum = attribute('maximum')
    excludes = attribute('excludes', [])
    origin = attribute('origin', 0)
    step = attribute('step', None)
    __options__ = SchemaBase.__options__ | set(['minimum', 'maximum', 'excludes', 'step', 'origin'])

    def __init__(self, *args, **kwds):
        ScalarSchema.__init__(self, *args, **kwds)
        if not isinstance(self.minimum, AttrRef) and not isinstance(self.maximum, AttrRef) and self.minimum > self.maximum and self.maximum is not None:
            throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'minmum($min) is bigger than maximum($max)', min=self.minimum, max=self.maximum)
        self.is_integer = False
        if self.excludes:
            if not isinstance(self.excludes, list) or not all(map(lambda a: isinstance(a, (int, Decimal)), self.excludes)):
                throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'excludes attribute must be list of number')
        if self.origin:
            if not isinstance(self.origin, (int, Decimal)):
                throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'origin attribute must be number')
        if self.step:
            if not isinstance(self.step, (int, Decimal)):
                throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'origin attribute must be number')

    def _validate(self, value):
        if not self.optional and value == None:
            raise JsonSchemaError(dict(msg=u'null is not allowed'))
        elif self.optional and value == None:
            return
        if self.is_integer:
            if not (isinstance(value, (int, long)) or (isinstance(value, Decimal) and value == int(value)))or isinstance(value, bool):
                raise JsonSchemaError(dict(msg=u'value should be $type', type='integer'), value, '')
        if isinstance(value, bool):
            raise JsonSchemaError(dict(msg=u'value should be $type', type='number'), value, '')
        if not isinstance(value, (Decimal, int, long)):
            raise JsonSchemaError(dict(msg=u'value should be $type', type='number'), value, '')
        if self.minimum != None and self.minimum > value:
            raise JsonSchemaError(dict(msg=u'value should be greater than $val', val=self.minimum), value, '')
        if self.maximum != None and self.maximum < value:
            raise JsonSchemaError(dict(msg=u'value should be smaller than $val', val=self.maximum), value, '')
        if self.excludes:
            if value in self.excludes:
                raise JsonSchemaError(dict(msg=u'value matched to exclusion pattern: $pattern', pattern='|'.join(map(str, self.excludes))))
        if self.step:
            if (value - self.origin) % self.step != 0:
                raise JsonSchemaError(dict(msg=u'valuie is not divisible: ($value - $origin) / $step', value=value, origin=self.origin, step=self.step), value, '')

    def intersect(self, another):
        minimum = max(self.minimum, another.minimum)
        if None in (self.maximum, another.maximum):
            maximum = self.maximum if another.maximum is None else another.maximum
        else:
            maximum = min(self.maximum, another.maximum)
        if minimum > maximum and maximum is not None:
            throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'minmum($min) is bigger than maximum($max)', min=minimum, max=maximum)
        is_integer = self.is_integer or another.is_integer
        excludes = []
        step = None
        origin = 0
        if self.step:
            if not another.step:
                step = self.step
                origin = self.origin
            else:
                if self.step > another.step:
                    s = self.step
                    o = self.origin
                    s2 = another.step
                    o2 = another.step
                else:
                    s = another.step
                    o = another.origin
                    s2 = self.step
                    o2 = self.origin
                i = 1
                while True:
                    n = s * i + o
                    if (n - o2) % s2 == 0:
                        step = self.step * another.step
                        origin = n
                        break
                    if i > 100: #アルゴリズムがアレなので、無限ループ防止
                        assert False
        elif another.step:
            step = another.step
            origin = another.origin
        if self.excludes:
            if another.excludes:
                excludes = list(set(self.excludes).union(set(another.excludes)))
            else:
                excludes = self.excludes
        opts = {
            'minimum': minimum,
            'maximum': maximum,
            'excludes': excludes,
            'origin': origin,
            'step': step,
        }
        r = self.clone(None, opts)
        r.is_integer = is_integer
        return r

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
            return u'integer'
        return u'number'

    @property
    def type(self):
        if self.is_integer:
            return u'integer'
        return u'number'

class IntegerSchema(NumberSchema):
    def __init__(self, *args, **kwds):
        NumberSchema.__init__(self, *args, **kwds)
        self.is_integer = True
