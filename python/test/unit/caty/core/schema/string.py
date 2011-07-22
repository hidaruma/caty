# coding: utf-8
from caty.testutil import TestCase
from caty.core.schema import *

class StringSchemaTest(TestCase):
    def test_validate_ok(self):
        scm = StringSchema()
        try:
            scm.validate(u'a')
            scm.validate(u'')
            scm.validate(u'abc')
        except Exception, e:
            self.fail(e)

    def test_validate_less_than_minLength(self):
        scm = StringSchema({'minLength':2})
        self.assertRaises(JsonSchemaError, scm.validate, u'a')
        try:
            scm.validate(u'ab')
        except Exception, e:
            self.fail(e)
    
    def test_validate_greater_than_maxLength(self):
        scm = StringSchema({'maxLength':3})
        self.assertRaises(JsonSchemaError, scm.validate, u'abcd')
        try:
            scm.validate(u'abc')
        except Exception, e:
            self.fail(e)

    def test_type_error(self):
        scm = StringSchema()
        self.assertRaises(JsonSchemaError, scm.validate, 0)
        self.assertRaises(JsonSchemaError, scm.validate, 'a')

    def test_convert(self):
        scm = StringSchema({'maxLength':3})
        v = scm.convert('100')
        self.assertEquals(u'100', v)
        self.assertRaises(JsonSchemaError, scm.convert, 1000)

