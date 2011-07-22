# coding: utf-8
from caty.testutil import TestCase
from caty.template.core.vm import *
from caty.template.core.loader import IBytecodeLoader

class MockLoader(IBytecodeLoader):
    u"""テスト用バイトコードローダー。
    あらかじめパス名とバイトコードを与えておき、
    load メソッドでは常にそのバイトコードを使い、
    store メソッドでは何もしない。
    """
    def __init__(self, *args, **kwds):
        self.codes = {}

    def store(self, path):
        pass

    def set_bytecode(self, path, code):
        u"""code は (opcode, value) のタプルのリストでもよい。
        """
        self.codes[path] = code

    def load(self, path):
        return self.codes[path]

def evaluate(vm, b):
    import codecs
    from StringIO import StringIO
    io = codecs.getwriter('utf-8')(StringIO())
    vm.write(b, io)
    io.seek(0)
    return io.read()

class VirtualMachineTest(TestCase):
    def testVariableReferrence(self):
        u"""変数参照のテスト
        """
        i = VirtualMachine(MockLoader())
        c = {'a': 'foo'}
        b = (
            (LOAD, 'a'),
            (POP, None),
        )
        i.context = Context(c)
        self.assertEquals('foo', evaluate(i, b))

    def testPush(self):
        u"""無名の値の表示テスト
        """
        i = VirtualMachine(MockLoader())
        b = (
            (PUSH, 'a'),
            (POP, None),
            (PUSH, 10),
            (POP, None),
        )
        self.assertEquals('a10', evaluate(i, b))

    def testJmp(self):
        u"""単純なラベル定義とジャンプのテスト
        """
        i = VirtualMachine(MockLoader())
        b = (
            (PUSH, 'a'),
            (POP, None),
            (JMP, 'label'),
            (PUSH, 10),
            (POP, None),
            (LABEL, 'label'),
            (PUSH, 'b'),
            (POP, None),
        )
        self.assertEquals('ab', evaluate(i, b))

    def testJmpUnless(self):
        u"""条件付きジャンプのテスト
        """
        i = VirtualMachine(MockLoader())
        b = (
            (PUSH, 'a'),
            (POP, None),
            (PUSH, True),
            (JMPUNLESS, 'label'),
            (PUSH, 10),
            (POP, None),
            (JMP, 'true'),
            (LABEL, 'label'),
            (PUSH, 'b'),
            (POP, None),
            (LABEL, 'true'),
            (PUSH, 'c'),
            (POP, None),
        )
        self.assertEquals('a10c', evaluate(i, b))

    def testNewCtx(self):
        u"""コンテキストリストの伸長のテスト
        """
        i = VirtualMachine(MockLoader())
        c = {'a': 'foo'}
        i.context = c
        b = (
            (NEWCTX, None),
        )
        evaluate(i, b)
        self.assertEquals(len(i.context.dict), 2)

    def testDelCtx(self):
        u"""コンテキストリストの削除のテスト
        """
        i = VirtualMachine(MockLoader())
        c = {'a': 'foo'}
        i.context = c
        b = (
            (NEWCTX, None),
            (DELCTX, None),
            (LOAD, 'a'),
            (POP, None)
        )
        self.assertEquals('foo', evaluate(i, b))
        self.assertEquals(len(i.context.dict), 1)
        
    def testCPush(self):
        u"""コンテキストに値を追加する
        """
        i = VirtualMachine(MockLoader())
        c = {'a': 'foo'}
        i.context = c
        b = (
            (NEWCTX, None),
            (PUSH, 'bar'),
            (CPUSH, 'a'),
            (LOAD, 'a'),
            (POP, None)
        )
        self.assertEquals('bar', evaluate(i, b))

    def testMacro(self):
        u"""マクロを呼び出す
        """
        i = VirtualMachine(MockLoader())
        c = {'a': 'funga'}
        i.context = c
        b = (
            (MACRO, 'macro1'),
            (LOAD, 'arg1'),
            (POP, None),
            (LOAD, 'arg2'),
            (POP, None),
            (RETURN, None),
            (NEWCTX, None),
            (PUSH, 'hoge'),
            (CPUSH, 'arg1'),
            (PUSH, 'fuga'),
            (CPUSH, 'arg2'),
            (EXPAND, 'macro1'),
            (LOAD, 'a'),
            (POP, None),
        )
        self.assertEquals('hogefugafunga', evaluate(i, b))

    def testEmptyLoop(self):
        u"""空ループ処理のテスト
        """
        i = VirtualMachine(MockLoader())
        c = {'l': []}
        i.context = c
        b = (
            (STRING, 'loop start'),
            (NEWCTX, None),
            (PUSH, 0),
            (CPUSH, 'index'),
            (PUSH, 1),
            (CPUSH, 'iteration'),
            (LOAD, 'l'),
            (LEN, 'l'),
            (CPUSH, 'count'),
            (LOAD, 'count'),
            (PUSH, 1),
            (LT, None),
            (JMPUNLESS, 'loopend'),
            (LABEL, 'loop'), # ループ開始
            
            (PUSH, 0),
            (LOAD, 'index'),
            (EQ, None),
            (CPUSH, 'first'),

            (LOAD, 'count'),
            (LOAD, 'iteration'),
            (EQ, None),
            (CPUSH, 'last'),
            
            (STRING, '\ndata = '),
            (LOAD, 'l'),
            (LOAD, 'index'),
            (AT, None),
            (POP, None),
            (STRING, '\n  index = '),
            (LOAD, 'index'),
            (POP, None),
            (STRING, '\n  iteration = '),
            (LOAD, 'iteration'),
            (POP, None),
            (STRING, '\n  first ? '),
            (LOAD, 'first'),
            (POP, None),
            (STRING, '\n  last ? '),
            (LOAD, 'last'),
            (POP, None),

            # ループ変数の更新
            (LOAD, 'index'),
            (PUSH, 1),
            (ADD, None),
            (CPUSH, 'index'),
            (LOAD, 'iteration'),
            (PUSH, 1),
            (ADD, None),
            (CPUSH, 'iteration'),

            (LOAD, 'last'),
            (JMPUNLESS, 'loop'),
            (DELCTX, None),
            (LABEL, 'loopend'),
            (STRING, '\nloop end\n')
        )
        expected = """loop start
loop end
"""
        result = evaluate(i, b)
        self.assertEquals(expected, result)

  
    def testLoop(self):
        u"""ループ処理のテスト
        ジャンプと比較演算などでループをエミュレート
        """
        i = VirtualMachine(MockLoader())
        c = {'l': ['foo', 'bar', 'buz']}
        i.context = c
        b = (
            (STRING, 'loop start'),
            (NEWCTX, None),
            (PUSH, 0),
            (CPUSH, 'index'),
            (PUSH, 1),
            (CPUSH, 'iteration'),
            (LOAD, 'l'),
            (LEN, 'l'),
            (CPUSH, 'count'),
            
            (LABEL, 'loop'), # ループ開始
            
            (PUSH, 0),
            (LOAD, 'index'),
            (EQ, None),
            (CPUSH, 'first'),

            (LOAD, 'count'),
            (LOAD, 'iteration'),
            (EQ, None),
            (CPUSH, 'last'),
            
            (STRING, '\ndata = '),
            (LOAD, 'l'),
            (LOAD, 'index'),
            (AT, None),
            (POP, None),
            (STRING, '\n  index = '),
            (LOAD, 'index'),
            (POP, None),
            (STRING, '\n  iteration = '),
            (LOAD, 'iteration'),
            (POP, None),
            (STRING, '\n  first ? '),
            (LOAD, 'first'),
            (POP, None),
            (STRING, '\n  last ? '),
            (LOAD, 'last'),
            (POP, None),

            # ループ変数の更新
            (LOAD, 'index'),
            (PUSH, 1),
            (ADD, None),
            (CPUSH, 'index'),
            (LOAD, 'iteration'),
            (PUSH, 1),
            (ADD, None),
            (CPUSH, 'iteration'),

            (LOAD, 'last'),
            (JMPUNLESS, 'loop'),
            (DELCTX, None),
            (STRING, '\nloop end\n')
        )
        expected = """loop start
data = foo
  index = 0
  iteration = 1
  first ? True
  last ? False
data = bar
  index = 1
  iteration = 2
  first ? False
  last ? False
data = buz
  index = 2
  iteration = 3
  first ? False
  last ? True
loop end
"""
        result = evaluate(i, b)
        self.assertEquals(expected, result)

    def tesDebugMode(self):
        u"""デバッグモードのテスト
        """
        i = VirtualMachine(MockLoader())
        i.debug = True
        c = {}
        b = (
            (LOAD, 'a'),
            (POP, None),
        )
        i.context = Context(c)
        self.assertEquals('$a', evaluate(i, b))
        b = (
            (STRING, 'loop start'),
            (NEWCTX, None),
            (PUSH, 0),
            (CPUSH, 'index'),
            (PUSH, 1),
            (CPUSH, 'iteration'),
            (LOAD, 'l'),
            (LEN, 'l'),
            (CPUSH, 'count'),
            (LOAD, 'count'),
            (PUSH, 1),
            (LT, None),
            (JMPUNLESS, 'loopend'),
            (LABEL, 'loop'), # ループ開始
            
            (PUSH, 0),
            (LOAD, 'index'),
            (EQ, None),
            (CPUSH, 'first'),

            (LOAD, 'count'),
            (LOAD, 'iteration'),
            (EQ, None),
            (CPUSH, 'last'),
            
            (STRING, '\ndata = '),
            (LOAD, 'l'),
            (LOAD, 'index'),
            (AT, None),
            (POP, None),
            (STRING, '\n  index = '),
            (LOAD, 'index'),
            (POP, None),
            (STRING, '\n  iteration = '),
            (LOAD, 'iteration'),
            (POP, None),
            (STRING, '\n  first ? '),
            (LOAD, 'first'),
            (POP, None),
            (STRING, '\n  last ? '),
            (LOAD, 'last'),
            (POP, None),

            # ループ変数の更新
            (LOAD, 'index'),
            (PUSH, 1),
            (ADD, None),
            (CPUSH, 'index'),
            (LOAD, 'iteration'),
            (PUSH, 1),
            (ADD, None),
            (CPUSH, 'iteration'),

            (LOAD, 'last'),
            (JMPUNLESS, 'loop'),
            (DELCTX, None),
            (LABEL, 'loopend'),
            (STRING, '\nloop end\n')
        )
        expected = """loop start
loop end
"""
        result = evaluate(i, b)
        self.assertEquals(expected, result)

