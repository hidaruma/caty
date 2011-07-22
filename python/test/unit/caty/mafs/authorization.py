# coding: utf-8
from caty.testutil import TestCase
from caty.mafs.authorization import *

def dummy(token, path, *args, **kwds):pass
path = '/path'
class ReaderGrantTest(TestCase):
    token = AuthoriToken('reader')
    def test_create(self):
        self.assertRaises(Exception, simple_checker(CREATE)(dummy), self.token, path)
    def test_update(self):
        self.assertRaises(Exception, simple_checker(UPDATE)(dummy), self.token, path)
    def test_delete(self):
        self.assertRaises(Exception, simple_checker(DELETE)(dummy), self.token, path)
    def test_read(self):
        self.assertNotRaises(simple_checker(READ)(dummy), self.token, path)

class UpdatorGrantTest(TestCase):
    token = AuthoriToken('updator')
    def test_create(self):
        self.assertNotRaises(simple_checker(CREATE)(dummy), self.token, path)
    def test_update(self):
        self.assertNotRaises(simple_checker(UPDATE)(dummy), self.token, path)
    def test_delete(self):
        self.assertNotRaises(simple_checker(DELETE)(dummy), self.token, path)
    def test_read(self):
        self.assertRaises(Exception, simple_checker(READ)(dummy), self.token, path)

class DualGrantTest(TestCase):
    token = AuthoriToken('dual')
    def test_create(self):
        self.assertNotRaises(simple_checker(CREATE)(dummy), self.token, path)
    def test_update(self):
        self.assertNotRaises(simple_checker(UPDATE)(dummy), self.token, path)
    def test_delete(self):
        self.assertNotRaises(simple_checker(DELETE)(dummy), self.token, path)
    def test_read(self):
        self.assertNotRaises(simple_checker(READ)(dummy), self.token, path)

