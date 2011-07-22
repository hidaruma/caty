from caty.testutil.testcase import *
from caty.template.core.instructions import *
from caty.template.core.st import *
from caty.template.core.compiler import ObjectCodeGenerator

def visit(node):
    v = ObjectCodeGenerator()
    return tuple(v.visit(node))

class STTest(TestCase):
    def testString(self):
        s = String(u'this is string')
        c = self.assertNotRaises(visit, s)
        self.assertEquals(c, ((STRING, u'this is string'),))

    def testVarLoad(self):
        vl = VarLoad('foo')
        c = self.assertNotRaises(visit, vl)
        self.assertEquals(c, ((LOAD, 'foo'),))
        
    def testVarDisp(self):
        vd = VarDisp()
        c = self.assertNotRaises(visit, vd)
        self.assertEquals(c, ((POP, None),))

    def testInclude(self):
        inc = Include('common.html')
        c = self.assertNotRaises(visit, inc)
        self.assertEquals(c, ((INCLUDE, 'common.html'),))

    def testFilterCall(self):
        f = FilterCall('f', [1,2,3])
        c = self.assertNotRaises(visit, f)
        expected = (
            (PUSH, 1),
            (PUSH, 2),
            (PUSH, 3),
            (CALL, ['f', 4]),
        )
        self.assertEquals(c, expected)

    def testIf1(self):
        i = If(VarLoad('foo'), 
               Template([String('subtempl')]), 
               [Null()], 
               Null())
        l = str(id(i))
        e = l + 'end'
        expected = (
            (LOAD, 'foo'),
            (JMPUNLESS, l),
            (STRING, 'subtempl'),
            (JMP, e),
            (LABEL, l),
            (LABEL, e),
        )
        c = self.assertNotRaises(visit, i)
        self.assertEquals(c, expected)

    def testIf2(self):
        el = Elif(VarLoad('bar'), Template([String('subtempl2')]))
        i = If(VarLoad('foo'), 
               Template([String('subtempl')]), 
               [el], 
               Null())
        l = str(id(i))
        l2 = str(id(el))
        e = l + 'end'
        expected = (
            (LOAD, 'foo'),
            (JMPUNLESS, l),
            (STRING, 'subtempl'),
            (JMP, e),
            (LABEL, l),
            (LOAD, 'bar'),
            (JMPUNLESS, l2),
            (STRING, 'subtempl2'),
            (JMP, e),
            (LABEL, l2),
            (LABEL, e),
        )
        c = self.assertNotRaises(visit, i)
        self.assertEquals(c, expected)

    def testIf3(self):
        el = Elif(VarLoad('bar'), Template([String('subtempl2')]))
        el2 = Elif(VarLoad('buz'), Template([String('subtempl3')]))
        i = If(VarLoad('foo'), 
               Template([String('subtempl')]), 
               [el, el2], 
               Null())
        l = str(id(i))
        l2 = str(id(el))
        l3 = str(id(el2))
        e = l + 'end'
        expected = (
            (LOAD, 'foo'),
            (JMPUNLESS, l),
            (STRING, 'subtempl'),
            (JMP, e),
            (LABEL, l),
            (LOAD, 'bar'),
            (JMPUNLESS, l2),
            (STRING, 'subtempl2'),
            (JMP, e),
            (LABEL, l2),
            (LOAD, 'buz'),
            (JMPUNLESS, l3),
            (STRING, 'subtempl3'),
            (JMP, e),
            (LABEL, l3),
            (LABEL, e),
        )
        c = self.assertNotRaises(visit, i)
        self.assertEquals(c, expected)

    def testIf4(self):
        el = Elif(VarLoad('bar'), Template([String('subtempl2')]))
        el2 = Elif(VarLoad('buz'), Template([String('subtempl3')]))
        els = Else(Template([String('subtempl4')]))
        i = If(VarLoad('foo'), 
               Template([String('subtempl')]), 
               [el, el2], 
               els)
        l = str(id(i))
        l2 = str(id(el))
        l3 = str(id(el2))
        e = l + 'end'
        expected = (
            (LOAD, 'foo'),
            (JMPUNLESS, l),
            (STRING, 'subtempl'),
            (JMP, e),
            (LABEL, l),
            (LOAD, 'bar'),
            (JMPUNLESS, l2),
            (STRING, 'subtempl2'),
            (JMP, e),
            (LABEL, l2),
            (LOAD, 'buz'),
            (JMPUNLESS, l3),
            (STRING, 'subtempl3'),
            (JMP, e),
            (LABEL, l3),
            (STRING, 'subtempl4'),
            (LABEL, e),
        )
        c = self.assertNotRaises(visit, i)
        self.assertEquals(c, expected)

    def testFor(self):
        n = Null()
        f = For('item',
                VarLoad('list'),
                'key',
                'index',
                'iteration',
                'counter',
                'first',
                'last',
                Template([String('subtemplate')]),
                n
        )
        l = str(id(f))
        e = l + 'end'
        nl = str(id(n))
        expected = (
            (NEWCTX, None),
            (PUSH, -1),
            (CPUSH, 'index'),
            (PUSH, 0),
            (CPUSH, 'iteration'),
            (LOAD, 'list'),
            (ENUM, None),
            (CPUSH, '__loop_item'),
            (LOAD, '__loop_item'),
            (LEN, None),
            (CPUSH, 'counter'),

            (LOAD, 'counter'),
            (PUSH, 0),
            (LT, None),
            (NOT, None),
            (JMPUNLESS, nl),

            (LABEL, l),

            (LOAD, 'index'),
            (PUSH, 1),
            (ADD, None),
            (CPUSH, 'index'),

            (LOAD, 'iteration'),
            (PUSH, 1),
            (ADD, None),
            (CPUSH, 'iteration'),

            (PUSH, 1),
            (LOAD, 'iteration'),
            (EQ, None),
            (CPUSH, 'first'),

            (LOAD, 'iteration'),
            (LOAD, 'counter'),
            (EQ, None),
            (CPUSH, 'last'),

            (LOAD, '__loop_item'),
            (LOAD, 'index'),
            (AT, None),
            (PUSH, 0),
            (AT, None),
            (CPUSH, 'key'),

            (LOAD, '__loop_item'),
            (LOAD, 'index'),
            (AT, None),
            (PUSH, 1),
            (AT, None),
            (CPUSH, 'item'),

            (STRING, 'subtemplate'),

            (CDEL, 'item'),
            (LOAD, 'last'),
            (JMPUNLESS, l),
            (JMP, e),

            (LABEL, nl),

            (LABEL, e),
            (DELCTX, None),

        )
        c = self.assertNotRaises(visit, f)
        i = 0
        for a, b in zip(c, expected):
            if a != b:
                print i,a,b
            i+=1
        self.assertEquals(c, expected)
        


