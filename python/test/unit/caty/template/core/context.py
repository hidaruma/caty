#coding:utf-8
from caty.testutil import TestCase
from caty.template.core.context import *

class ContextTest(TestCase):
    def testDefaultContext(self):
        u"""通常のアクセスのテスト
        """
        c = Context({
            'a': 'foo',
            'b': 'bar'
        })
        self.assertEquals('foo', c['a'])
        self.assertEquals('bar', c['b'])

    def testHierarcalAccess(self):
        u""".による階層アクセスのテスト
        """
        c = Context({
            'a': {
                'b': 'boo',
                'c': {
                    'd': 'damn',
                }
            }
        }
        )
        self.assertEquals('boo', c['a.b'])
        self.assertEquals('damn', c['a.c.d'])

    def testShadowing(self):
        u"""複数の辞書で同じキーが定義されてる場合のテスト
        最も直近に追加されたコンテキストが参照されるのが正しい
        """
        c = Context({'a': 'foo'})
        c.new({})
        c['a'] = 'bar'
        self.assertEquals('bar', c['a'])

    def testNew(self):
        u"""新規の辞書をコンテキストに追加する
        """
        c = Context({'a': 'foo'})
        c.new({'b': 'bar'})
        self.assertEquals('bar', c['b'])
        self.assertEquals(2, len(c.dict))

    def testDelete(self):
        u"""コンテキストから辞書を削除
        """
        c = Context({'a': 'foo'})
        c.new({'b': 'bar'})
        c.delete()
        self.assertEquals(1, len(c.dict))

    def testCannotAddingToDefaultContext(self):
        u"""デフォルトの辞書への追加操作が失敗するかのテスト
        """
        c = Context({'a': 'foo'})
        try:
            c['b'] = 'bar'
            self.fail()
        except TemplateRuntimeError, e:
            pass
        except:
            self.fail()

    def testCannotDeleteDefaultContext(self):
        u"""デフォルトの辞書が削除されないことのテスト
        """
        c = Context({'a': 'foo'})
        try:
            c.delete()
            self.fail()
        except TemplateRuntimeError, e:
            pass
        except:
            self.fail()

    def testAddingHierarcalData(self):
        u""".で連結された階層キーのセット
        """
        c = Context({'a': 'foo'})
        c.new({})
        c['x.y.z'] = 'buz'
        c['x.y.a'] = 'buz?'
        self.assertEquals('buz', c['x.y.z'])
        self.assertEquals('buz?', c['x.y.a'])
        self.assertTrue(isinstance(c.dict[0]['x'], dict))
        self.assertTrue(isinstance(c.dict[0]['x']['y'], dict))
        self.assertFalse(isinstance(c.dict[0]['x']['y']['z'], dict))

    def testGet(self):
        u"""辞書の同メソッドと同じ動作かのテスト
        """
        c = Context({'a': 'foo'})
        v = c.get('x', 0)
        self.assertEquals(0, v)

    def testIndexAccess(self):
        u"""a.1.b のようなインデックスアクセスへの対応テスト
        """
        c = Context({'a': [{'b':1}, {'b':2}]})
        v = self.assertNotRaises(c.get, 'a.0.b')
        self.assertEquals(v, 1)

