# coding: utf-8
from StringIO import StringIO
from topdown import *
from caty.core.casm.language.schemaparser import schema
from caty.core.casm.language.util import *
from caty.core.casm.language.ast import *
from caty.testutil import TestCase, test

def parse(s):
    def schemata(seq):
        r = []
        while not seq.eof:
            r.append(schema(seq))
        return r
    return as_parser(schemata).run(remove_comment(s), auto_remove_ws=True)

class SchemaParserTest(TestCase):
    def test_simple_scalar_type(self):
        s = 'type foo = pkg.mod:Foo;'
        node = parse(s)[0]
        self.assertTrue(isinstance(node, TypeReference))
        self.assertEquals(node.name, 'foo')
        self.assertTrue(isinstance(node.definition, ScalarNode))
        self.assertEquals(node.definition.schema_name, 'pkg.mod:Foo')
        s = 'type foo = pkg:$;'
        node = parse(s)[0]
        s = 'type $ = {"fuga" :  string};'
        node = parse(s)[0]

        s = 'type x = app:mod:foo;'
        node = parse(s)[0]

    def test_simple_optional1(self):
        s = 'type foo = pkg.mod:Foo;'
        node = parse(s)[0]
        self.assertTrue(isinstance(node, TypeReference))
        self.assertEquals(node.name, 'foo')
        self.assertTrue(isinstance(node.definition, ScalarNode))
        self.assertEquals(node.definition.schema_name, 'pkg.mod:Foo')

    def test_simple_optional2(self):
        s = 'type foo = (pkg.mod:Foo);'
        node = parse(s)[0]
        self.assertTrue(isinstance(node, TypeReference))
        self.assertEquals(node.name, 'foo')
        self.assertTrue(isinstance(node.definition, ScalarNode))
        self.assertEquals(node.definition.schema_name, 'pkg.mod:Foo')

    def test_simple_scalar_type_with_opts(self):
        s = 'type foo = integer(maximum=10, minimun=5);'
        node = parse(s)[0]
        self.assertTrue(isinstance(node.definition, ScalarNode))
        self.assertEquals(node.definition.schema_name, 'integer')
        self.assertEquals(node.definition.options, {'maximum': 10, 'minimun': 5})

    def test_simple_type_with_udt(self):
        s = 'type foo = [integer, string, boolean];'
        node = parse(s)[0]
        self.assertTrue(isinstance(node.definition, ScalarNode))
        self.assertEquals(node.definition.schema_name, 'array')
        self.assertEquals(node.definition.options, {})
        self.assertTrue(any(map(lambda a: isinstance(a, ScalarNode), node.definition.items)))

    def test_simple_type_repeat(self):
        s = 'type foo = [integer, string, boolean*];'
        node = parse(s)[0]
        self.assertTrue(node.definition.options['repeat'])
        s = 'type foo = [(integer|string)*];'
        node = parse(s)[0]
        self.assertTrue(node.definition.options['repeat'])
        s = """type bar = [foo*];"""
        node = parse(s)[0]
        self.assertTrue(node.definition.options['repeat'])

    def test_simple_union_type(self):
        s = 'type foo = integer | string;'
        node = parse(s)[0]
        self.assertTrue(isinstance(node.definition, UnionNode))
        self.assertTrue(isinstance(node.definition.node1, ScalarNode))
        self.assertTrue(isinstance(node.definition.node2, ScalarNode))

        s = 'type foo = (integer | string | boolean);'
        node = parse(s)[0]
        self.assertTrue(isinstance(node.definition, UnionNode))
        self.assertTrue(isinstance(node.definition.node1, UnionNode))
        self.assertTrue(isinstance(node.definition.node2, ScalarNode))

    def test_simple_union_with_tag(self):
        s = 'type foo = @i integer | @s string;'
        node = parse(s)[0]
        self.assertTrue(isinstance(node.definition, UnionNode))
        self.assertTrue(isinstance(node.definition.node1, TaggedNode))
        self.assertTrue(isinstance(node.definition.node2, TaggedNode))

    def test_simple_multiple_decl(self):
        s = 'type foo = string;\ntype bar = integer;'
        node1 = parse(s)[0]
        node2 = parse(s)[1]
        self.assertTrue(isinstance(node1, TypeReference))
        self.assertEquals(node1.name, 'foo')
        self.assertTrue(isinstance(node1.definition, ScalarNode))
        self.assertEquals(node1.definition.schema_name, 'string')

        self.assertTrue(isinstance(node2, TypeReference))
        self.assertEquals(node2.name, 'bar')
        self.assertTrue(isinstance(node2.definition, ScalarNode))
        self.assertEquals(node2.definition.schema_name, 'integer')

    def test_object(self):
        s = """type foo = {
            "a": string,
            "b": boolean,
            *: any
        };
        """
        node = parse(s)[0]
        self.assertTrue(isinstance(node, TypeReference))
        self.assertEquals(node.name, 'foo')
        self.assertTrue(isinstance(node.definition, ObjectNode))
        n = node.definition
        self.assertTrue('a' in n.items)
        self.assertEquals(n.items['a'].schema_name, 'string')
        self.assertTrue('b' in n.items)
        self.assertEquals(n.items['b'].schema_name, 'boolean')
        self.assertTrue(isinstance(n.wildcard, ScalarNode))

    def test_nested_object(self):
        s = """type foo = {
            "a": string,
            "b": {
                "c": boolean?,
                "d": (integer)
            }
        };
        """
        node = parse(s)[0]
        self.assertTrue(isinstance(node, TypeReference))
        self.assertEquals(node.name, 'foo')
        self.assertTrue(isinstance(node.definition, ObjectNode))
        n = node.definition
        self.assertTrue('a' in n.items)
        self.assertTrue('b' in n.items)
        
        b = n.items['b']
        self.assertTrue('c' in b.items)
        self.assertEquals(b.items['c'].schema_name, 'boolean')
        self.assertEquals(b.items['c'].optional, True)
        self.assertTrue('d' in b.items)
        self.assertEquals(b.items['d'].schema_name, 'integer')
 
        s = """type bar = [{"x": string, "y": integer}*];"""
        node = parse(s)[0]
        self.assertTrue(isinstance(node, TypeReference))
        self.assertEquals(node.name, 'bar')
        n = node.definition.items[0]
        self.assertTrue(isinstance(n, ObjectNode))
        self.assertTrue('x' in n.items)
        self.assertTrue('y' in n.items)

    def test_enum(self):
        s = 'type foo = "a" | "b" | "c";'
        node = parse(s)[0]
        self.assertTrue(isinstance(node.definition, EnumNode))

        s = 'type foo = 0 | 1 | 2;'
        node = parse(s)[0]
        self.assertTrue(isinstance(node.definition, EnumNode))

        s = 'type foo = "a" | "b" | 1;'
        self.assertRaises(ValueError, parse, s)

    def test_intersection(self):
        s = """type foo = {
            "a": string,
            *:any
        } & {"b": integer, *:any };
        """
        node = parse(s)[0]
        self.assertTrue(isinstance(node.definition, IntersectionNode))
        s2 = 'type x = (foo & bar);'
        node = parse(s2)[0]
        self.assertTrue(isinstance(node.definition, IntersectionNode))

    def test_updater(self):
        s1 = 'type x = {"a":string} << {"b": integer};'
        self.assertNotRaises(lambda :parse(s1))

