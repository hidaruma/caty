# coding: utf-8
from caty.shell.shebang import parse
from caty.testutil import TestCase

no_shebang = u"""
<!DOCTYPE html
  PUBLIC '-//W3C//DTD XHTML 1.0 Strict//EN'
    'http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd'>
<html>
    <title>test</title>
    <p>test</p>
</html>
"""

meta = u"""<?caty-meta template="smarty"?>
<!DOCTYPE html
  PUBLIC '-//W3C//DTD XHTML 1.0 Strict//EN'
    'http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd'>
<html>
    <title>test</title>
    <p>test</p>
</html>
"""


script = u"""<?caty-script 
    do {
        cmd >: "foo"
    }
?>
<!DOCTYPE html
  PUBLIC '-//W3C//DTD XHTML 1.0 Strict//EN'
    'http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd'>
<html>
    <title>test</title>
    <p>test</p>
</html>
"""

meta_and_script = u"""<?caty-meta template="smarty"?>
<?caty-script 
    do {
        cmd >: "foo"
    }
?>
<!DOCTYPE html
  PUBLIC '-//W3C//DTD XHTML 1.0 Strict//EN'
    'http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd'>
<html>
    <title>test</title>
    <p>test</p>
</html>
"""

class ShebangTest(TestCase):
    def test_no_shebang(self):
        m, s, c = parse(no_shebang, True)
        self.assertTrue(not m)
        self.assertTrue(not s)
        self.assertEquals(c.strip(), no_shebang.strip())

    def test_meta(self):
        m, s, c = parse(meta, True)
        self.assertEquals(m, {'template': 'smarty'})
        self.assertTrue(not s)
        self.assertEquals(c.strip(), no_shebang.strip())

    def test_script(self):
        m, s, c = parse(script, True)
        self.assertTrue(not m)
        self.assertEquals(s.strip(), 'do {\n        cmd >: "foo"\n    }')
        self.assertEquals(c.strip(), no_shebang.strip())

    def test_all(self):
        m, s, c = parse(meta_and_script, True)
        self.assertEquals(m, {'template': 'smarty'})
        self.assertEquals(s.strip(), 'do {\n        cmd >: "foo"\n    }')
        self.assertEquals(c.strip(), no_shebang.strip())

    def test_no_shebang2(self):
        m, s, c = parse(no_shebang)
        self.assertTrue(not m)
        self.assertTrue(not s)
        self.assertEquals(c.strip(), no_shebang.strip())

    def test_meta2(self):
        m, s, c = parse(meta)
        self.assertEquals(m, {'template': 'smarty'})
        self.assertTrue(not s)
        self.assertEquals(c.strip(), no_shebang.strip())

    def test_script2(self):
        m, s, c = parse(script)
        self.assertTrue(not m)
        self.assertTrue(not s)
        self.assertEquals(c.strip(), no_shebang.strip())

    def test_all2(self):
        m, s, c = parse(meta_and_script)
        self.assertEquals(m, {'template': 'smarty'})
        self.assertTrue(not s)
        self.assertEquals(c.strip(), no_shebang.strip())



