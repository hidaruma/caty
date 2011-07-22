# coding: utf-8
import codecs
from StringIO import StringIO
from caty.template.genshi.translator import GenshiTranslator, GenshiTemplateError
from caty.testutil import TestCase

def translate(s):
    gt = GenshiTranslator()
    gt.feed(s)
    gt.close()
    return str(gt)

class GenshiTranslatorTest(TestCase):
    def testVarRef(self):
        u"""変数参照の構文の変換テスト。
        ${foo} という形式から Smarty 風の {$foo} に変更される。
        """
        s = """<?xml version="1.0"?>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:c="http://chimaira.org/caty/template">
    <p>${xxx}</p>
    <p>${qwerty|filter}</p>
    <p>${abc|foo:"bar":"buz"}</p>
</html>"""
        r = translate(s)
        self.assertTrue('<p>{$qwerty|filter}</p>' in r)
        self.assertTrue('<p>{$xxx}</p>' in r)
        self.assertTrue('<p>{$abc|foo:"bar":"buz"}</p>' in r)

        self.assertTrue('<p>${xxx}</p>' not in r)
        self.assertTrue('<p>${qwerty|filter}</p>' not in r)
        self.assertTrue('<p>${xxx}</p>' not in r)

    def testIf(self):
        u"""if 文のテスト。
        <p c:if="cond">bar</p> が {if $cond}...{/fi} となることを確認する。
        """
        s = """<?xml version="1.0"?>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:c="http://chimaira.org/caty/template">
    <p c:if="cond">bar</p>
</html>"""
        r = translate(s)
        self.assertTrue('{if $cond}<p>bar</p>{/if}' in r)

    def testIfBlock(self):
        u"""c:block 属性でグループ化された if 文のテスト。
        """

        s = """<?xml version="1.0"?>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:c="http://chimaira.org/caty/template">
    <p c:if="cond" c:block="start">bar</p>
    <p c:block="end">boo</p>
</html>"""
        r = translate(s)
        self.assertTrue('{if $cond}<p>bar</p>' in r)
        self.assertTrue('<p>boo</p>{/if}')

    def testIfNest(self):
        u"""ネストした if 文であっても正しくハンドルできる事を確認する。
        """
        s = """<?xml version="1.0"?>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:c="http://chimaira.org/caty/template">
    <div c:if="cond">bar
        <div c:if="cond2" c:block="start">boo</div>
        <div c:block="end">buz</div>
    </div>
</html>"""
        r = translate(s)
        e = """<?xml version="1.0"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:c="http://chimaira.org/caty/template">
    {if $cond}<div>bar
        {if $cond2}<div>boo</div>
        <div>buz</div>{/if}
    </div>{/if}
</html>"""
        self.assertEquals(r, e)

