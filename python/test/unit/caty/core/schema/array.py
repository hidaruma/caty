# coding: utf-8
from caty.core.schema import *
from caty.testutil import TestCase

class ArraySchemaTest(TestCase):
    def test_validate_ok(self):
        scm = ArraySchema(
                        options={'maxItems':10, 'optional':True, 'repeat':True}, 
                        schema_list=[NumberSchema(dict(is_integer=True)), StringSchema()])
        self.assertNotRaises(scm.validate, [])
        self.assertNotRaises(scm.validate, [0])
        self.assertNotRaises(scm.validate, [0, u'1', u'2', u'3', u'4', u'5', u'6', u'7', u'8', u'9'])

    def test_type_error(self):
        scm = ArraySchema(
                        options={'repeat':True, 'minItems':1},
                        schema_list=[StringSchema(), StringSchema()])
        self.assertRaises(JsonSchemaError, scm.validate, [u'a', u'b', 1])
        self.assertRaises(JsonSchemaError, scm.validate, [True])
        self.assertRaises(JsonSchemaError, scm.validate, u'a')
        self.assertRaises(JsonSchemaError, scm.validate, [])

    def test_overflow_max(self):
        scm = ArraySchema(
                        options={'maxItems':10, 'repeat':True},
                        schema_list = [NumberSchema({'is_integer':True})])
        self.assertNotRaises(scm.validate, list(range(10)))
        self.assertRaises(JsonSchemaError, scm.validate, list(range(11)))

    def test_convert(self):
        scm = ArraySchema(
                        options={'repeat':True}, 
                        schema_list=[StringSchema(), BoolSchema(), NumberSchema(options={'is_integer':True})])
        expected = [u'abc', True, 1, 2]
        converted = scm.convert([u'abc', u'true', u'1', u'2'])
        self.assertEquals(converted, expected)

