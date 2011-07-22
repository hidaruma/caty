# coding: utf-8
from StringIO import StringIO
from topdown import *
from caty.core.casm.language.commandparser import command
from caty.core.casm.language.util import *
from caty.core.casm.language.ast import *
from caty.testutil import TestCase, test

def parse(s):
    return as_parser(command).run(remove_comment(s), auto_remove_ws=True)

class CommandParserTest(TestCase):
    def test_simple_decl(self):
        s = 'command foo {} [] :: string -> string refers python:Command;'
        self.assertNotRaises(parse, s)
        s = 'command foo :: string -> string refers python:foo.bar.Command;'
        self.assertNotRaises(parse, s)
        s = '/** doc string */\ncommand foo :: string -> string refers python:foo.bar.Command;'
        self.assertNotRaises(parse, s)
        s = '/* comment */\ncommand foo {} [] :: object -> object refers python:foo.bar.Command;'
        self.assertNotRaises(parse, s)

    def test_decl_with_opts(self):
        s = 'command foo {"x":integer} [] :: string -> string refers python:foo.bar.Command;'
        self.assertNotRaises(parse, s)

        s = 'command foo {"y":1|2|3} [] :: string -> string refers python:foo.bar.Command;'
        self.assertNotRaises(parse, s)

        s = 'command foo {"x":integer, "y":string?} [] :: string -> string refers python:foo.bar.Command;'
        self.assertNotRaises(parse, s)

        s = 'command foo {"x":integer, "hjkl":string?} [] :: string -> string refers python:foo.bar.Command;'
        self.assertNotRaises(parse, s)

    def test_multi_decl(self):
        s = 'command foo {"x":integer} [] :: string -> string refers python:foo.bar.Command;'
        s = s + 'command bar :: string -> string refers python:foo.bar.Command2;'
        self.assertNotRaises(parse, s)

    def test_overload(self):
        s = 'command foo {"x":integer} [] :: string -> string'
        s = s + ' refers python:foo.bar.Command;'
        self.assertNotRaises(parse, s)
        
    def test_jump_decl(self):
        s = """command foo :: string -> string
        throws Error
        refers python:foo.bar.Command;
        """
        self.assertNotRaises(parse, s)

        s = """command foo :: string -> string
        throws [Error1, Erro2]
        refers python:foo.bar.Command;
        """
        self.assertNotRaises(parse, s)

        s = """command foo :: string -> string
        breaks Ret
        refers python:foo.bar.Command;
        """
        self.assertNotRaises(parse, s)

        s = """command foo :: string -> string
        breaks [Ret1, Ret2]
        refers python:foo.bar.Command;
        """
        self.assertNotRaises(parse, s)

        s = """command foo :: string -> string
        breaks Ret
        throws Error
        refers python:foo.bar.Command;
        """
        self.assertNotRaises(parse, s)

    def test_resource_decl(self):
        s = """command foo :: string -> string
        uses mafs
        refers python:foo.bar.Command;
        """
        self.assertNotRaises(parse, s)

        s = """command foo :: string -> string
        reads [mafs, env]
        refers python:foo.bar.Command;
        """
        self.assertNotRaises(parse, s)


        s = """command foo :: string -> string
        reads mafs
        updates env
        refers python:foo.bar.Command;
        """
        self.assertNotRaises(parse, s)

    def test_heavy_overload(self):
        s = """command buz
        :: string -> string
        
        [string, integer] :: null -> string

        {"x":integer} [string] :: null -> string

        refers python:foo.bar.Command3;
        """
        self.assertNotRaises(parse, s)

    def test_with_docstring(self):
        s = """/** 
            documentation comment 
        */
        command foo {} [] :: string -> string refers python:foo.bar.Command;"""
        self.assertNotRaises(parse, s)
        
    def test_annotation(self):
        s = """
        @annotation command foo {} [] :: string -> string refers python:foo.bar.Command;
        """
        self.assertNotRaises(parse, s)

    def test_typevariable(self):
        s1 = """
        command foo :: string -> _T refers python:foo.bar.Command;
        """
        self.assertNotRaises(parse, s1)
        s2 = """
        command foo :: _T -> string refers python:foo.bar.Command;
        """
        self.assertNotRaises(parse, s2)
        s3 = """
        command foo :: string -> @FOO _T | @BAR null refers python:foo.bar.Command;
        """
        self.assertNotRaises(parse, s2)
        
        
