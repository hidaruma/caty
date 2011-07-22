# coding: utf-8
from caty.testutil import TestCase
from caty.web.util import *

class UtilTest(TestCase):
    def test_get_virtual_path1(self):
        self.assertEquals(get_virtual_path('/foo', '/foo/'), '/')

    def test_get_virtual_path2(self):
        self.assertEquals(get_virtual_path('/foo', '/foo/index.html'), '/index.html')

    def test_get_virtual_path3(self):
        self.assertEquals(get_virtual_path('/foo', '/foo'), '')

