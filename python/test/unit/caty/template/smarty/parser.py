from caty.testutil import TestCase
from caty.template.smarty.parser import smarty_parser
from caty.template.core.compiler import STDebugger

class SmartyParserTest(TestCase):
    def test_simple(self):
        s = """<p>{$foo}</p>
        """
        t = self.assertNotRaises(smarty_parser.run, s)
        d = STDebugger()
        r = list(d.visit(t))
        e = ['Template', 'String', 'Template', 'Load', 'Disp', 'String']
        self.assertEquals(r, e)

    def test_loop1(self):
        s = """<ul>
        {foreach from=$item item=i}
        <li>{$i}</li>
        {/foreach}
        </ul>
        """
        t = self.assertNotRaises(smarty_parser.run, s)
        d = STDebugger()
        r = list(d.visit(t))
        e = ['Template', 'String', 'For', 'Load', 'Template', 'String', 'Template', 'Load', 'Disp', 'String', 'Null', 'String']
        self.assertEquals(r, e)

    def test_loop2(self):
        pass

