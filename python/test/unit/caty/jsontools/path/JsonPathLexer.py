# coding: utf-8
from caty.testutil import *
from caty.jsontools.path.JsonPathLexer import *
from StringIO import StringIO

def mk_lexer(s):
    io = StringIO()
    io.write(s)
    io.seek(0)
    return Lexer(io)

class LexerTest(TestCase):
    def test_lex(self):
        lexer = mk_lexer('$;')
        self.assertEquals([ROOT], list([t.getType() for t in lexer]))
        
        lexer = mk_lexer('$.foo;')
        self.assertEquals([ROOT, PATH], list([t.getType() for t in lexer]))
        
        lexer = mk_lexer('$.foo.bar;')
        self.assertEquals([ROOT, PATH, PATH], list([t.getType() for t in lexer]))
        
        lexer = mk_lexer('$.foo : array;')
        self.assertEquals([ROOT, PATH, SCHEMATYPE], list([t.getType() for t in lexer]))
        
        lexer = mk_lexer('$.foo : array?;')
        self.assertEquals([ROOT, PATH, SCHEMATYPE], list([t.getType() for t in lexer]))
        
        lexer = mk_lexer('$.foo : array*;')
        self.assertEquals([ROOT, PATH, SCHEMATYPE], list([t.getType() for t in lexer]))

        lexer = mk_lexer('$.foo : array [integer];')
        self.assertEquals([ROOT, PATH, SCHEMATYPE], list([t.getType() for t in lexer]))

        lexer = mk_lexer('$.foo : array [integer, string];')
        self.assertEquals([ROOT, PATH, SCHEMATYPE], list([t.getType() for t in lexer]))

        lexer = mk_lexer('$.foo : array [integer, string] , maxItems=10;')
        self.assertEquals([ROOT, PATH, SCHEMATYPE], list([t.getType() for t in lexer]))

        lexer = mk_lexer('$.foo : array [integer, string] , maxItems=10, optional=false;')
        self.assertEquals([ROOT, PATH, SCHEMATYPE], list([t.getType() for t in lexer]))


        lexer = mk_lexer("""$.foo.buz : array [integer, string] , maxItems=10, optional=false;
$.foo.bar:string;""")
        tokens = list([(t.getType(), t.getText()) for t in lexer])
        tokens = [t[0] for t in tokens]
        self.assertEquals([ROOT, PATH, PATH, SCHEMATYPE, ROOT, PATH, PATH, SCHEMATYPE], tokens)


