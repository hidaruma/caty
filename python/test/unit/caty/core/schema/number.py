# coding: utf-8
from caty.testutil import TestCase
from caty.core.schema import *
from decimal import Decimal

class NumberSchemaTest(TestCase):
    def test_validate_ok(self):
        scm = NumberSchema({})
        try:
            scm.validate(Decimal('0.0'))
            scm.validate(Decimal('1.0'))
            scm.validate(Decimal('-1.0'))
            scm.validate(Decimal('1'))
        except Exception, e:
            self.fail(e)

    def test_validate_less_than_minimum(self):
        scm = NumberSchema({'minimum':Decimal('10.0')})
        self.assertRaises(JsonSchemaError, scm.validate, Decimal('9.0'))
        try:
            scm.validate(Decimal('10.0'))
        except Exception, e:
            self.fail(e)
    
    def test_validate_greater_than_maximum(self):
        scm = NumberSchema({'maximum':Decimal('10.0')})
        self.assertRaises(JsonSchemaError, scm.validate, Decimal('11.0'))
        try:
            scm.validate(Decimal('10.0'))
        except Exception, e:
            self.fail(e)

    def test_type_error(self):
        scm = NumberSchema({})
        self.assertRaises(JsonSchemaError, scm.validate, '1')
        self.assertRaises(JsonSchemaError, scm.validate, 'a')

    def test_convert(self):
        scm = NumberSchema({'maximum':Decimal('10.0')})
        v = scm.convert('1.1')
        self.assertEquals(Decimal('1.1'), v)
        v = scm.convert('1')
        self.assertEquals(1, v)
        self.assertRaises(JsonSchemaError, scm.convert, 'a')
        self.assertRaises(JsonSchemaError, scm.convert, '12.0')

