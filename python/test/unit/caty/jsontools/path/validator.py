# coding: utf-8
from caty.testutil import *
from caty.jsontools.path.validator import *

def mk_schema(s):
    return to_decl_style(s)

class ValidatorTest(TestCase):
    def test_validate1(self):
        scm = mk_schema(
        """$.foo: string;
$.bar: integer;""")
        print scm

    def test_validate2(self):
        scm = mk_schema('$.foo.#: string;')
        print scm

    def test_validate3(self):
        scm = mk_schema(
        """$.foo: string;
$.bar: integer;
$.buz.hoge.huga: string;
$.buz.hoge.hage: string;
""")
        print scm


    def test_validate4(self):
        scm = mk_schema(
        """$.0: string;
$.1: integer;
$.2.foo: string;
$.2.bar: string;
$.#.foo: string;
$.#.bar: string;
""")
        print scm

if __name__ == '__main__': 
    test(ValidatorTest)

