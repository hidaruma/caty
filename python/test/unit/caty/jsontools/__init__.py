# coding: utf-8
import caty.jsontools as json
from caty.testutil import TestCase
import os
import decimal

class JsonTest(TestCase):
    def test_load(self):
        f = open('test.json', 'wb')
        f.write('{"a": "foo", "b":1, "c": {"d": 2}}')
        f.close()
        try:
            fo = open('test.json')
            j = json.load(fo)
            self.assertEquals('foo', j['a'])
            self.assertEquals(1, j['b'])
            self.assertEquals(2, j['c']['d'])
            fo.close()
        finally:
            os.remove('test.json')

    def test_loads(self):
        s = '{"a": "foo", "b":1, "c": {"d": 2}}'
        j = json.loads(s)
        self.assertEquals('foo', j['a'])
        self.assertEquals(1, j['b'])
        self.assertEquals(2, j['c']['d'])

    def test_dump(self):
        j = {"a": "b"}
        try:
            fo = open('test.json', 'wb')
            json.dump(j, fo)
            fo.close()
            loaded = json.load(open('test.json'))
            self.assertEquals(j, loaded)
            fo.close()
        finally:
            os.remove('test.json')

    def test_dumps(self):
        j = {"a": "b"}
        s = json.dumps(j)
        self.assertEquals(json.loads(s), j)

    def test_encode_decode(self):
        j = json.TaggedValue('t1', {'a': 1, 'b': json.TaggedValue('t2', 2), 'c': json.TagOnly('t3')})
        self.assertEquals(json.encode(j), {'$tag': 't1', '$val': {'a': 1, 'b': {'$tag': 't2', '$val': 2}, 'c': {'$tag': 't3', '$no-value': True}}})
        self.assertEquals(json.decode(json.encode(j)), j)


    def test_tag(self):
        self.assertEquals(json.tag(1), 'integer')
        self.assertEquals(json.tag(u's'), 'string')
        self.assertEquals(json.tag([]), 'array')
        self.assertEquals(json.tag({}), 'object')
        self.assertEquals(json.tag(None), 'null')
        self.assertEquals(json.tag(decimal.Decimal('1.0')), 'number')

    def _test_obj2path(self, o, p):
        self.assertEquals(json.obj2path(o), p)
        self.assertEquals(json.path2obj(p), o)

    def test_obj2path1(self):
        o = {
            'a': 1,
            'b': {
                'c': 2
            }
        }
        p = {
            '$.a': 1,
            '$.b.c': 2
        }
        self._test_obj2path(o, p)

    def test_obj2path2(self):
        o = {
            'a': 1,
            'b': [
                'a',
                'b',
                'c'
            ]
        }
        p = {
            '$.a': 1,
            '$.b.0': 'a',
            '$.b.1': 'b',
            '$.b.2': 'c'
        }
        self._test_obj2path(o, p)

    def test_obj2path3(self):
        o = {
            'a': 1,
            'b': {
                'c': [
                    {'x': 1, 'y':2}
                ]
            }
        }
        p = {
            '$.a': 1,
            '$.b.c.0.x': 1,
            '$.b.c.0.y': 2,
        }
        self._test_obj2path(o, p)

