#coding: utf-8
from caty.core.schema.base import *
import caty.core.runtimeobject as ro
import random

class BoolSchema(ScalarSchema):

    def _validate(self, value):
        if not self.optional and value == None:
            raise JsonSchemaError(ro.i18n.get('null is not allowed'))
        elif self.optional and value == None:
            return
        if not isinstance(value, bool):
            raise JsonSchemaError(ro.i18n.get(u'value should be $type', type='boolean'))

    def _convert(self, value):
        if value == 'true': return True
        if value == 'false': return False
        raise JsonSchemaError(ro.i18n.get(u'An error occuered while converting to $type', type='boolean'), value, '')

    def intersect(self, another):
        return self.clone()

    def dump(self, depth, node=[]):
        return 'boolean'

    def generate(self):
        return random.choice([True, False])

    @property
    def type(self):
        return 'boolean'

