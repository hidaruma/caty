#coding: utf-8
from caty.testutil import TestCase
from caty.util.cache import *
from functools import partial

class MemoizeTest(TestCase):
    def test_memoized(self):
        def foo(a, b):
            return a() + b()

        def _(d):
            d['x'] += 1
            return d['x']

        d1 = {'x': 0}
        x = partial(_, d1)
        d2 = {'x': 1}
        y = partial(_, d2)
        m = self.assertNotRaises(memoize, foo)
        v = self.assertNotRaises(m, x, y)
        self.assertEquals(v, 3)
        self.assertEquals(d1['x'], 1)
        self.assertEquals(d2['x'], 2)
        v = self.assertNotRaises(m, x, y)
        self.assertEquals(v, 3)
        self.assertEquals(d1['x'], 1)
        self.assertEquals(d2['x'], 2)
        m.clear()
        v = self.assertNotRaises(m, x, y)
        self.assertEquals(v, 5)
        self.assertEquals(d1['x'], 2)
        self.assertEquals(d2['x'], 3)

    def test_cannot_memoized(self):
        def foo(a, b):
            return (a, b)

        m = self.assertNotRaises(memoize, foo)
        self.assertRaises(Exception, m, [], {})

class CacheTest(TestCase):
    def test_cache(self):
        cache = Cache(101)
        for i in range(100):
            cache.set(i, i**2)

        for i in range(11, 100):
            self.assertEquals(cache.get(i), i**2)
        cache.set(100, 100**2)
        # 1..11 が削除されているはず
        for i in range(1, 11):
            self.assertEquals(cache.get(i), None)
        self.assertEquals(cache.get(100), 100**2)
        
        for i in range(20, 101):
            self.assertEquals(cache.get(i), i**2)

        for i in range(101, 111):
            cache.set(i, i**2)
            cache.get(i)
            cache.get(i)

        # 0, 11..20 が削除されているはず
        for i in range(10, 20):
            self.assertEquals(cache.get(i), None)
        
