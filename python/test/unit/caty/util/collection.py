#coding: utf-8
from caty.testutil import TestCase
from caty.util import merge_dict
class MergeDict(TestCase):
    def test_no_conflict(self):
        x = {'a': 1, 'b': 2}
        y = {'c': 3, 'd': 4}
        z = merge_dict(x, y)
        self.assertEquals(1, z['a'])
        self.assertEquals(2, z['b'])
        self.assertEquals(3, z['c'])
        self.assertEquals(4, z['d'])
        self.assertEquals(len(x), 2)
        self.assertEquals(len(y), 2)

    def test_pre(self):
        x = {'a': 1, 'b': 2}
        y = {'b': 3, 'd': 4}
        z = merge_dict(x, y, 'pre')
        self.assertEquals(1, z['a'])
        self.assertEquals(2, z['b'])
        self.assertEquals(4, z['d'])

    def test_post(self):
        x = {'a': 1, 'b': 2}
        y = {'b': 3, 'd': 4}
        z = merge_dict(x, y, 'post')
        self.assertEquals(1, z['a'])
        self.assertEquals(3, z['b'])
        self.assertEquals(4, z['d'])

    def test_error(self):
        x = {'a': 1, 'b': 2}
        y = {'b': 3, 'd': 4}
        self.assertRaises(Exception, merge_dict, x, y, 'error')

    def test_callback(self):
        x = {'a': 1, 'b': 2}
        y = {'b': 3, 'd': 4}
        z = merge_dict(x, y, lambda a, b: 0 if a>b else 1)
        self.assertEquals(1, z['a'])
        self.assertEquals(3, z['b'])
        self.assertEquals(4, z['d'])


