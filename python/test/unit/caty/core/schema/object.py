# coding: utf-8
from caty.testutil import TestCase
from caty.core.schema import *
from decimal import Decimal

class ObjectSchemaTest(TestCase):
    def test_validate_ok1(self):
        scm = ObjectSchema(schema_obj={
            'foo': StringSchema(),
            'bar': BoolSchema()
        })
        self.assertNotRaises(scm.validate, {'foo':u'string', 'bar':True})

    def test_validate_ok2(self):
        scm = ObjectSchema()
        items = {
            'foo': StringSchema(),
            'bar': BoolSchema()
        }
        scm2 = scm.clone(schema_obj=items)
        self.assertNotRaises(scm2.validate, {'foo':u'string', 'bar':True})

    def test_validate_ok3(self):
        scm = ObjectSchema(schema_obj={
            'foo': StringSchema(),
            'bar': BoolSchema()
        }, wildcard=NumberSchema())
        self.assertNotRaises(scm.validate, {'foo':u'string', 'bar':True, 'x':Decimal('1.0')})

    def test_validate_error1(self):
        scm = ObjectSchema(schema_obj={
            'foo': StringSchema(),
            'bar': BoolSchema()
        })
        self.assertRaises(JsonSchemaError, scm.validate, {'foo':u'string', 'bar':1.0})

    def test_validate_error2(self):
        scm = ObjectSchema(schema_obj={
            'foo': StringSchema(),
            'bar': BoolSchema()
        })
        self.assertRaises(JsonSchemaError, scm.validate, {'foo':u'string', 'bar':True, 'unknown': 1})

    def test_validate_error3(self):
        scm = ObjectSchema(schema_obj={
            'foo': StringSchema(),
            'bar': BoolSchema()
        }, wildcard=NumberSchema())
        self.assertRaises(JsonSchemaError, scm.validate, {'foo':u'string', 'bar':True, 'x':u's'})

    def test_convert_ok1(self):
        scm = ObjectSchema(schema_obj={
            'foo': StringSchema(),
            'bar': BoolSchema()
        })
        r = self.assertNotRaises(scm.convert, {'foo':'string', 'bar':'true'})
        self.assertEquals({'foo':u'string', 'bar': True}, r)

    def test_convert_ok2(self):
        scm = ObjectSchema()
        items = {
            'foo': StringSchema(),
            'bar': BoolSchema()
        }
        scm.schema_obj = items
        r = self.assertNotRaises(scm.convert, {'foo':'string', 'bar':'true'})
        self.assertEquals({'foo':u'string', 'bar': True}, r)

    def test_convert_ok3(self):
        scm = ObjectSchema(schema_obj={
            'foo': StringSchema(),
            'bar': BoolSchema()
        }, wildcard=NumberSchema())
        r = self.assertNotRaises(scm.convert, {'foo':'string', 'bar':'true', 'x': '1.0'})
        self.assertEquals({'foo':u'string', 'bar': True, 'x': Decimal('1.0')}, r)

    def test_convert_error1(self):
        scm = ObjectSchema(schema_obj={
            'foo': StringSchema(),
            'bar': BoolSchema()
        })
        self.assertRaises(JsonSchemaError, scm.convert, {'foo':'string', 'bar':'1.0'})

    def test_convert_error2(self):
        scm = ObjectSchema(schema_obj={
            'foo': StringSchema(),
            'bar': BoolSchema()
        })
        self.assertRaises(JsonSchemaError, scm.convert, {'foo':'string', 'bar':'true', 'unknown': '1'})

    def test_convert_error3(self):
        scm = ObjectSchema(schema_obj={
            'foo': StringSchema(),
            'bar': BoolSchema()
        }, wildcard=NumberSchema())
        self.assertRaises(JsonSchemaError, scm.convert, {'foo':'string', 'bar':'true', 'x':'s'})

    def test_updater(self):
        scm1 = ObjectSchema(schema_obj={
            'foo': StringSchema(),
            'bar': BoolSchema()
        })
        scm2 = ObjectSchema(schema_obj={
            'hoge': StringSchema(),
            'hage': BoolSchema()
        })
        new = scm1 << scm2
        self.assertNotRaises(new.validate, {'foo': u'a', 
                                            'bar': True,
                                            'hoge':u'b',
                                            'hage': False})

