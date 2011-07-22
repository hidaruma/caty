# coding: utf-8
from caty.core.schema.enum import *
from caty.testutil import TestCase

class EnumSchemaTest(TestCase):
    def test_validate_ok(self):
        scm = EnumSchema([u'foo', u'bar', u'buz'])
        self.assertNotRaises(scm.validate, u'foo')
        self.assertNotRaises(scm.validate, u'bar')
        self.assertNotRaises(scm.validate, u'buz')

    def test_type_error(self):
        scm = EnumSchema([u'foo', u'bar', u'buz'])
        self.assertRaises(JsonSchemaError, scm.validate, 'f')
        self.assertRaises(JsonSchemaError, scm.validate, 0)



