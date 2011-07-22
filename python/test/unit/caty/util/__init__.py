#coding: utf-8
from caty.testutil import TestCase
from caty.util import try_parse
from decimal import Decimal
class TryParse(TestCase):
    def test1(self):
        v = try_parse(int, '1')
        self.assertEquals(v, 1)

    def test2(self):
        v = try_parse(Decimal, '1.0')
        self.assertEquals(v, Decimal('1.0'))

    def test3(self):
        v = try_parse(bool, 'True')
        self.assertEquals(v, True)

    def test4(self):
        v = try_parse(int, 's')
        self.assertEquals(v, None)


