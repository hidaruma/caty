# coding: utf-8
import unittest
from caty.util import get_message

class TestCase(unittest.TestCase):
    u"""拡張テストケース。
    """
    def assertNotRaises(self, test, *args, **kwds):
        u"""例外が送出されないことのみを確認したいテストで用いる。
        """
        try:
            return test(*args, **kwds)
        except Exception, e:
            import traceback
            print traceback.format_exc()
            print get_message(e, 'utf-8')
            self.fail(e)

import sys
def test(*testcases):
    u"""テスト一覧の実行。
    引数は可変長引数なので、任意の数の TestCase のクラスを指定する。
    すべてのテストが成功したら終了ステータス 0 でプロセスを終了し、
    一つでも失敗したケースがあれば終了ステータス 1 でプロセスを終了する。
    """
    result = unittest.TestResult()
    suite = unittest.TestSuite()
    for t in testcases:
        suite.addTest(unittest.makeSuite(t))
    suite.run(result)
    if not result.wasSuccessful():
        print '--------'.join(('%s:\n%s' % (f[0]._testMethodName, f[1]) for f in result.failures + result.errors))
        return 1
    return 0

