# coding: utf-8
# FileObject, DirectoryObject は常に他のモジュールを必要としている。
# そのためこれらのクラス単体でのテストはあまり意味がない。
# 代わりに builder モジュールのテストケースに mix-in させるクラスを定義する。
from __future__ import with_statement
from datetime import datetime
import time
from caty.mafs.fileobject import *
from caty.mafs.authorization import *
from caty.mafs import stdfs
from caty.mafs.metadata import MetadataRegistrar
import sys

class FileObjectTest(object):
    def create_fo(self, path, mode='rb'):
        raise NotImplementedError

    def testCreate(self):
        f = self.create_fo('./data/foo.txt', 'wb')
        try:
            self.assertTrue(os.path.exists('./data/foo.txt'))
        finally:
            os.remove('./data/foo.txt')

    def testWrite(self):
        try:
            with self.create_fo('./data/foo.txt', 'wb') as f:
                f.write('a')
                f.write('b')
            self.assertEquals(open('./data/foo.txt').read(), 'ab')
        except Exception, e:
            print e
            raise 
        finally:
            os.remove('./data/foo.txt')

    def testRead(self):
        open('./data/foo.txt', 'wb').write('abc\ndef')
        try:
            f = self.create_fo('./data/foo.txt')
            self.assertEquals('abc\ndef', f.read())
        finally:
            os.remove('./data/foo.txt')

    def testRemoveCatyEncoding(self):
        open('./data/foo.txt', 'wb').write('abc\ndef')
        try:
            f = self.create_fo('./data/foo.txt')
            self.assertEquals('abc\ndef', f.read())
            self.assertEquals('utf-8', f.encoding)
        finally:
            os.remove('./data/foo.txt')

    def testDelete(self):
        open('./data/foo.txt', 'wb')
        try:
            f = self.create_fo('./data/foo.txt')
            f.delete(None)
            self.assertFalse(os.path.exists('./data/foo.txt'))
        finally:
            if os.path.exists('./data/foo.txt'):
                os.remove('./data/foo.txt')

    def testIsModifiedSince(self):
        open('./data/foo.txt', 'wb')
        try:
            f = self.create_fo('./data/foo.txt')
            self.assertTrue(f.is_modifed_since(100.0))
            self.assertFalse(f.is_modifed_since(time.time() + 1000.0))
        finally:
            os.remove('./data/foo.txt')

    def testGetMetadata(self):
        open('./data/foo.txt', 'wb').write('abc')
        try:
            f = self.create_fo('./data/foo.txt')
            self.assertTrue(isinstance(f.last_modified, datetime))
            self.assertFalse(f.is_hidden)
            self.assertFalse(f.is_executable)
            self.assertEquals('utf-8', f.encoding)
            self.assertEquals(3, f.content_length)
            self.assertEquals('text/plain', f.content_type)
            self.assertTrue(f.is_text)
        finally:
            os.remove('./data/foo.txt')

class DirectoryObjectTest(object):
    def create_do(self, path):
        raise NotImplementedError

    def testCreate(self):
        d = self.create_do('./data/bar')
        try:
            d.create()
            self.assertTrue(os.path.exists('./data/bar'))
        finally:
            os.rmdir('./data/bar')

    def testRead(self):
        os.makedirs('./data/bar/buz/boo')
        open('./data/bar/foo.txt', 'wb')
        open('./data/bar/buz/foo.txt', 'wb')
        open('./data/bar/buz/boo/foo.txt', 'wb')
        try:
            d = self.create_do('./data/bar')
            entries = list(d.read())
            self.assertEquals(2, len(entries))
            entries = list(d.read(True))
            self.assertEquals(3, len(entries))
        finally:
            os.remove('./data/bar/buz/foo.txt')
            os.remove('./data/bar/buz/boo/foo.txt')
            os.remove('./data/bar/foo.txt')
            os.rmdir('./data/bar/buz/boo')
            os.rmdir('./data/bar/buz')
            os.rmdir('./data/bar')

