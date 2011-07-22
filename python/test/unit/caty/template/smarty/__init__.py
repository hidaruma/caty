from caty.testutil import *
from caty.template.smarty import SmartyTemplate
from StringIO import StringIO
from csslib.selector import *

class SmartyTemplateTest(TestCase):
    def test_varref(self):
        t = SmartyTemplate('template_test/smarty1.html')
        t.context = {'title': 'test'}
        s = StringIO()
        t.write(s)
        s.seek(0)
        self.assertEquals(select(s.read(), 'title').next().text, 'test')

    def test_loop(self):
        t = SmartyTemplate('template_test/smarty2.html')
        t.context = {'list': ['foo', 'bar']}
        s = StringIO()
        t.write(s)
        s.seek(0)
        i = select(s.read(), 'li')
        self.assertEquals(i.next().text, 'foo')
        self.assertEquals(i.next().text, 'bar')

    def test_loop2(self):
        t = SmartyTemplate('template_test/smarty2.html')
        t.context = {'list': []}
        s = StringIO()
        t.write(s)
        s.seek(0)
        i = select(s.read(), 'li')
        self.assertEquals(i.next().text, 'nothing')

