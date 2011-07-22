# coding: utf-8
from caty.testutil  import TestCase
from caty.mafs.stdfs import *
from caty.mafs.metadata import *
import os

class StdFsTest(TestCase):
    def setUp(self):
        if not os.path.exists('data'):
            os.mkdir('data')
    
    def trearDown(self):
        if os.path.exists('data'):
            os.removedirs('data')

    def test_createFile(self):
        createFile('./data/test.txt')
        self.assertTrue(os.path.exists('./data/test.txt'))
        os.remove('./data/test.txt')

    def test_putFile(self):
        putFile('./data/test.txt', 'aaa')
        self.assertEquals('aaa', open('./data/test.txt').read())
        os.remove('./data/test.txt')

    def test_createDirectory(self):
        createDirectory('./data/foo')
        self.assertTrue(os.path.exists('./data/foo'))
        self.assertTrue(os.path.isdir('./data/foo'))
        createDirectory('./data/bar')
        createDirectory('./data/bar/buz')
        self.assertTrue(os.path.exists('./data/bar/buz'))
        self.assertTrue(os.path.isdir('./data/bar/buz'))
        os.rmdir('./data/foo')
        os.rmdir('./data/bar/buz')
        os.rmdir('./data/bar')

    def test_deleteFile(self):
        open('./data/foo.txt', 'wb').write('a')
        deleteFile('./data/foo.txt')
        self.assertTrue(not os.path.exists('./data/foo.txt'))

    def test_deleteDirectory(self):
        os.mkdir('./data/foo')
        deleteDirectory('./data/foo')
        self.assertTrue(not os.path.exists('./data/foo'))
        os.makedirs('./data/bar/buz')
        deleteDirectory('./data/bar/buz')
        self.assertTrue(not os.path.exists('./data/bar/buz'))
        deleteDirectory('./data/bar')
        self.assertTrue(not os.path.exists('./data/bar'))

    def test_delete(self):
        open('./data/foo.txt', 'wb').write('a')
        delete('./data/foo.txt')
        self.assertTrue(not os.path.exists('./data/foo.txt'))
        os.mkdir('./data/bar')
        delete('./data/bar')
        self.assertTrue(not os.path.exists('./data/bar'))

    def test_readFile(self):
        open('./data/foo.txt', 'wb').write('a')
        self.assertEquals('a', readFile('./data/foo.txt'))
        deleteFile('./data/foo.txt')
    
    def test_readDirectory(self):
        os.makedirs('./data/bar/buz/boo')
        open('./data/bar/abc.txt', 'wb')
        open('./data/bar/xyz.txt', 'wb')
        entries = readDirectory('./data/bar')
        names = set([e.name for e in entries])
        self.assertEquals(set(['buz', 'abc.txt', 'xyz.txt']), set(names))
        os.remove('./data/bar/abc.txt')
        os.remove('./data/bar/xyz.txt')
        os.rmdir('./data/bar/buz/boo')
        os.rmdir('./data/bar/buz')
        os.rmdir('./data/bar')

    def test_writeFile(self):
        open('./data/foo.txt', 'wb')
        writeFile('./data/foo.txt', './data/foo')
        self.assertEquals('./data/foo', open('./data/foo.txt').read())
        os.remove('./data/foo.txt')

    def test_getMetadata_from_text_file(self):
        open('./data/foo.txt', 'wb').write('abc')
        meta = getMetadata('./data/foo.txt')
        self.assertFalse(meta.is_dir)
        self.assertEquals(3, meta.contentLength)
        self.assertEquals(timestamp(os.stat('./data/foo.txt').st_mtime), meta.lastModified)
        self.assertFalse(meta.executable)
        self.assertEquals('text/plain', meta.contentType)
        self.assertTrue(meta.isText)
        os.remove('./data/foo.txt')

    def test_getMetadata_from_directory(self):
        os.makedirs('./data/bar/buz/boo')
        open('./data/bar/abc.txt', 'wb')
        open('./data/bar/xyz.txt', 'wb')

        meta = getMetadata('./data/bar')
        self.assertEquals(timestamp(os.stat('./data/bar').st_mtime), meta.lastModified)

        os.remove('./data/bar/abc.txt')
        os.remove('./data/bar/xyz.txt')
        os.rmdir('./data/bar/buz/boo')
        os.rmdir('./data/bar/buz')
        os.rmdir('./data/bar')

