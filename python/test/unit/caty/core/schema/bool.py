# coding: utf-8
from caty.core.schema import *
from caty.testutil import TestCase

class BoolSchemaTest(TestCase):
    def test_validate_ok(self):
        scm = BoolSchema({})
        try:
            scm.validate(True)
            scm.validate(False)
        except Exception, e:
            self.fail(e)

    def test_type_error(self):
        scm = BoolSchema({})
        self.assertRaises(JsonSchemaError, scm.validate, 0)
        self.assertRaises(JsonSchemaError, scm.validate, 'a')

    def test_convert(self):
        scm = BoolSchema({})
        v = scm.convert('true')
        self.assertEquals(True, v)
        v = scm.convert('false')
        self.assertEquals(False, v)

