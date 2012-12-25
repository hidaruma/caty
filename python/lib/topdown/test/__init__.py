from topdown.test.charseq import *
import types
import unittest

def test_all():
    suite = unittest.TestSuite()
    for k, v in globals().items():
        if isinstance(v, types.TypeType) and issubclass(v, unittest.TestCase):
            suite.addTest(unittest.makeSuite(v))
    return suite

