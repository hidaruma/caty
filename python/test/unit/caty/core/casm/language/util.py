# coding: utf-8
from StringIO import StringIO
from topdown import *
from caty.core.casm.language.util import *
from caty.testutil import TestCase, test
def parse(p, s):
    return as_parser(p).run(remove_comment(s), auto_remove_ws=True)

class UtilTest(TestCase):
    def test_annotation(self):
        v = self.assertNotRaises(parse, annotation, '@annotation')
        self.assertEquals('annotation', v)

