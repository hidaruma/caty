# coding: utf-8
import os
from caty.testutil import TestCase
from caty.mafs.builder import *
from caty.mafs.authorization import AuthoriToken

def mafs():
    return build_mafs_module(root_dir=os.getcwd())

class MafsBuilderTest(TestCase):
    def testHasEnoughFunction(self):
        mod = mafs()
        self.assertTrue(hasattr(mod, 'createFile'))
        self.assertTrue(hasattr(mod, 'putFile'))
        self.assertTrue(hasattr(mod, 'createDirectory'))
        self.assertTrue(hasattr(mod, 'readFile'))
        self.assertTrue(hasattr(mod, 'readDirectory'))
        self.assertTrue(hasattr(mod, 'delete'))
        self.assertTrue(hasattr(mod, 'deleteFile'))
        self.assertTrue(hasattr(mod, 'deleteDirectory'))
        self.assertTrue(hasattr(mod, 'writeFile'))
        self.assertTrue(hasattr(mod, 'getMetadata'))

    def test_createFile(self):
        mod = mafs()
        try:
            mod.createFile('/foo.txt')
            self.assertTrue(os.path.exists('foo.txt'))
        finally:
            os.remove('foo.txt')

    def test_getMetadata(self):
        mod = mafs()
        open('foo.txt', 'wb').write('aaa')
        try:
            metadata = mod.getMetadata('/foo.txt')
            self.assertTrue(metadata.isText)
        finally:
            os.remove('foo.txt')

